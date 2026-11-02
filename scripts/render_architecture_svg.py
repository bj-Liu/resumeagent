"""Render a presentation-size SVG of the source-backed architecture (stdlib only)."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    parts=['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1100" role="img" aria-labelledby="title desc">
<title id="title">ResumeAgent system architecture</title><desc id="desc">GUI, CLI and official MCP enter Harness Runtime. Runtime manages three agent roles, tools, state, budget, context and traces. Refiner evaluation and artifact validation form an integrated quality role. SQLite checkpoints enable recovery; evaluation tests the entire workflow.</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#6c8b72"/></marker></defs>
<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#193b31}.title{font-size:28px;font-weight:650}.heading{font-size:18px;font-weight:600}.label{font-size:14px}.small{font-size:12px;fill:#65766b}.wire{fill:none;stroke:#6c8b72;stroke-width:2;marker-end:url(#arrow)}.dash{stroke-dasharray:5 5}</style>
<rect width="1600" height="1100" rx="14" fill="#fafbf7"/>
<text x="50" y="52" class="title">ResumeAgent / system architecture</text>
<text x="50" y="80" class="label">One execution owner. Three business roles. Durable, observable website generation.</text>''']
    def box(x,y,w,h,title,lines=(),fill='#ffffff',stroke='#cbd9c5',dashed=False):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}"'+(' stroke-dasharray="6 4"' if dashed else '')+'/>')
        parts.append(f'<text x="{x+20}" y="{y+29}" class="heading">{escape(title)}</text>')
        for i,line in enumerate(lines):
            parts.append(f'<text x="{x+20}" y="{y+55+i*21}" class="label">{escape(line)}</text>')
    def wire(path,label=None,x=0,y=0,dashed=False):
        parts.append(f'<path d="{path}" class="wire'+(' dash' if dashed else '')+'"/>')
        if label: parts.append(f'<text x="{x}" y="{y}" class="small">{escape(label)}</text>')
    box(50,115,290,82,'User interface / GUI',['Tkinter studio'],fill='#eef4e8')
    box(365,115,225,82,'CLI',['Run controls'],fill='#eef4e8')
    box(740,115,300,82,'External MCP Client',['Official SDK / local stdio'])
    box(1110,115,440,82,'MCP Server + JobManager',['Validated tools → bounded background Runs'])
    wire('M1040 156H1110')
    wire('M195 197V220H500V245')
    wire('M477 197V220')
    wire('M1330 197V220H1120V245')
    box(50,245,1500,243,'Harness Runtime — execution management center',[],fill='#e5eee3',stroke='#a7bd9e')
    parts.append('<text x="75" y="310" class="label">Create → plan → concurrent page generation → render → evaluate → bounded refinement → validate → complete</text>')
    parts.append('<text x="75" y="337" class="small">Finite retries · conditional branches · cancellation · request and Run deadlines · artifact-aware checkpoint recovery</text>')
    services=[('State','Run / Task / Page','SQLite checkpoints'),('Context','Stage-specific inputs','Bounded history'),('Budget','Tokens / estimated cost','Limits / concurrency'),('Tools','Validated registry','Traceable I/O'),('Tracing','Run-queryable events','Redacted diagnostics'),('Persistence','Private local artifacts','Checksums / files')]
    for index,(name,a,b) in enumerate(services): box(75+index*245,360,225,105,name,[a,b],fill='#f9fbf6')
    wire('M455 488V546','managed business calls',475,519)
    wire('M1315 488V546','managed tool calls',1335,519)
    box(50,546,990,173,'Agent layer — three composed mixins',[],fill='#f2f5ec')
    box(72,595,296,101,'Planner',['Facts → page specifications','Shared design language'])
    box(386,595,296,101,'Generator',['Page specification → HTML/CSS','Concurrent page workers'])
    box(700,595,318,101,'Refiner',['Screenshot → evaluation / revision','Visual feedback + user feedback'])
    wire('M368 644H386')
    wire('M682 644H700')
    box(1090,546,460,173,'Tools — actual operations',['Browser / Selenium: render and capture','Filesystem: save source, images, backups','Validator: filenames, artifacts and HTML'],fill='#eef4e8')
    wire('M1090 690H1040V677H1018','screenshot',1048,680)
    wire('M350 719V788','managed model requests',370,754)
    box(50,788,610,142,'LLM Client → LLM Provider',['OpenAI / Azure OpenAI / DashScope-Qwen','Provider usage observer → Runtime Budget','A usable vision model, quota and network are required'])
    wire('M860 719V788')
    box(710,788,390,142,'Quality Agent role',['Integrated gate, not a separate class','Refiner screenshot judgment','+ Filesystem artifact validation'],fill='#fcf7df',stroke='#c6b674',dashed=True)
    wire('M1315 719V759H1000V788','artifact validation',1160,747)
    wire('M1100 858H1150')
    box(1150,788,400,142,'Output + checkpoint',['Website files and screenshots','Completed or resumable Run','State verifies completed artifacts'])
    box(50,973,1500,81,'Evaluation — tests the managed workflow',['Workflow / Recovery / paired Benchmark / independent blinded visual rubric. HTML validity is not a visual-quality score.'],fill='#eaf0e5')
    wire('M1530 973V938',dashed=True)
    parts.append('<text x="50" y="1080" class="small">Source: harness/, resumeagent/agents/, resumeagent/tools/, resumeagent/mcp_server.py, storage/, evals/ · no independent QualityAgent class</text></svg>')
    svg='\n'.join(parts)
    for target in ('docs/architecture.svg','showcase/assets/architecture.svg'):
        (ROOT/target).write_text(svg+'\n',encoding='utf-8')
    print('Rendered source-backed 1600 × 1100 presentation SVG.')


if __name__=='__main__':
    render()
