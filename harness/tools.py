"""Validated Tool Registry: agents call this boundary, implementations own actual I/O."""
import asyncio
from dataclasses import dataclass
import inspect
from pathlib import Path
import time
from resumeagent.tools.filesystem_helpers import read_json, write_json
from .context import CURRENT_EXECUTION
from .tracing import safe_error


class ToolError(RuntimeError):
    pass


class ToolValidationError(ToolError):
    pass


@dataclass(frozen=True)
class Parameter:
    type: type | tuple
    required: bool = True
    default: object = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    function: object
    validator: object = None


@dataclass(frozen=True)
class ToolResult:
    name: str
    value: object
    duration_ms: float


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, description, parameters, function, validator=None):
        if name in self._tools:
            raise ValueError(f'Duplicate tool: {name}')
        self._tools[name] = Tool(name, description, parameters, function, validator)

    def describe(self):
        return [{'name': t.name, 'description': t.description,
                 'parameters': {k: {'type': str(v.type), 'required': v.required} for k,v in t.parameters.items()}}
                for t in self._tools.values()]

    def _prepare(self, name, arguments):
        if name not in self._tools:
            raise ToolValidationError('Unknown tool')
        tool = self._tools[name]
        if arguments.keys() - tool.parameters.keys():
            raise ToolValidationError('Unexpected tool parameters')
        values = dict(arguments)
        for key, definition in tool.parameters.items():
            if key not in values:
                if definition.required:
                    raise ToolValidationError('Missing tool parameter')
                values[key] = definition.default
            if not isinstance(values[key], definition.type):
                raise ToolValidationError('Invalid tool parameter type')
        if tool.validator:
            tool.validator(values)
        return tool, values

    def _emit(self, event, **fields):
        scope = CURRENT_EXECUTION.get()
        if scope:
            scope.runtime.tracer.emit(scope.run_id, event, **fields)

    def _check(self):
        scope = CURRENT_EXECUTION.get()
        if scope:
            scope.runtime.budget.check()

    def call(self, name, **arguments):
        started = time.monotonic()
        try:
            self._check()
            tool, values = self._prepare(name, arguments)
            if inspect.iscoroutinefunction(tool.function):
                raise ToolValidationError('Use acall for asynchronous tools')
            self._emit('tool.started', tool=name, parameter_names=list(values))
            value = tool.function(**values)
            elapsed = (time.monotonic()-started)*1000
            self._emit('tool.completed', tool=name, status='completed', duration_ms=elapsed)
            return ToolResult(name, value, elapsed)
        except Exception as exc:
            self._emit('tool.failed', tool=name, error=safe_error(exc), duration_ms=(time.monotonic()-started)*1000)
            raise

    async def acall(self, name, **arguments):
        started = time.monotonic()
        try:
            self._check()
            tool, values = self._prepare(name, arguments)
            self._emit('tool.started', tool=name, parameter_names=list(values))
            if inspect.iscoroutinefunction(tool.function):
                value = await tool.function(**values)
            else:
                scope = CURRENT_EXECUTION.get()
                if scope is not None:
                    worker = asyncio.create_task(asyncio.to_thread(tool.function, **values))
                    scope.runtime.track_tool(worker, name)
                    value = await asyncio.shield(worker)
                else:
                    value = await asyncio.to_thread(tool.function, **values)
            self._check()
            elapsed = (time.monotonic()-started)*1000
            self._emit('tool.completed', tool=name, status='completed', duration_ms=elapsed)
            return ToolResult(name, value, elapsed)
        except asyncio.CancelledError:
            self._emit('tool.cancelled', tool=name, status='cancelled')
            raise
        except Exception as exc:
            self._emit('tool.failed', tool=name, error=safe_error(exc), duration_ms=(time.monotonic()-started)*1000)
            raise


def build_tools(agent):
    tools = ToolRegistry()
    path_parameter = {'path': Parameter(str)}
    def writable(values):
        path = Path(values['path']).resolve()
        if not path.is_relative_to(Path(agent.save_file).resolve()):
            raise ToolValidationError('Output path escapes the run directory')
    tools.register('filesystem.exists', 'Check a file exists', path_parameter, lambda path: Path(path).is_file())
    tools.register('filesystem.read_text', 'Read UTF-8 text', path_parameter, lambda path: Path(path).read_text(encoding='utf-8'))
    tools.register('filesystem.read_json', 'Read a JSON document', path_parameter, read_json)
    tools.register('filesystem.write_json', 'Atomically save a JSON document', {**path_parameter,'data':Parameter((dict,list))},
                   lambda path,data: write_json(path, data, ensure_ascii=False), writable)
    tools.register('filesystem.save_page', 'Save generated HTML/CSS and process image references',
                   {'page_info':Parameter(dict),'html':Parameter(str),'css':Parameter((str,type(None)),False,None)}, agent.persist_html_css_async)
    tools.register('filesystem.read_page', 'Read the current HTML/CSS for refinement', {'page_info':Parameter(dict)}, agent.read_page)
    tools.register('filesystem.validate_page', 'Validate generated files, HTML and screenshot', {'page_info':Parameter(dict),'require_screenshot':Parameter(bool,False,True)}, agent.validate_page)
    tools.register('filesystem.check_artifacts', 'Check checkpoint artifacts and optional checksums',
                   {'files':Parameter(dict),'fingerprints':Parameter((dict,type(None)),False,None)}, agent.check_artifacts)
    tools.register('filesystem.validate_plan', 'Validate page filenames and duplicate pages', {'pages':Parameter(list)}, agent.validate_plan)
    def render(html_path, screenshot_path):
        agent.webserver.get_screenshot(html_path,screenshot_path)
        return {'screenshot': screenshot_path}
    def valid_render(values):
        for value in values.values():
            writable({'path':value})
    tools.register('browser.render', 'Render a local webpage and save its screenshot',
                   {'html_path':Parameter(str),'screenshot_path':Parameter(str)}, render, valid_render)
    tools.register('browser.preview', 'Open a generated page in a preview browser', {'html_path':Parameter(str)}, lambda html_path: agent.webserver.open_website(html_path))
    return tools
