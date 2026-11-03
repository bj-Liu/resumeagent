"""Launch the existing GUI with conservative CNY budgets for a recorded live demo.

No form automation, model mocks or alternative scheduler are installed here.
Enter examples/fixtures/zhang_san_demo.json through the actual GUI.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from harness.budget import BudgetLimits
from resumeagent.main import HomepageDesignAgent
from resumeagent.frontend.gui import Application
from resumeagent.tools.browser import Webserver


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default=f'test-artifacts/showcase-live-{datetime.now():%Y%m%d-%H%M%S}')
    parser.add_argument('--driver-path')
    args=parser.parse_args()
    folder=Path(args.folder).resolve()
    folder.mkdir(parents=True,exist_ok=False)
    # Deliberately above the documented Beijing 0.8/2.7 rates: these are
    # conservative budget units, not a provider invoice or new billing logic.
    limits=BudgetLimits(max_cost=5,max_iterations=1,max_concurrency=2,
                        max_prompt_tokens=400000,max_completion_tokens=120000,
                        request_timeout=180,max_run_seconds=1200,max_retries=1,
                        prices={'qwen3.8-flash':[10,50]})
    browser=Webserver(str(folder/'website'),web_type='edge',driver_path=args.driver_path)
    agent=HomepageDesignAgent(model='qwen3.8-flash',save_file=str(folder/'website'),browser=browser,
        runtime_options={'storage_root':str(folder/'state'),'limits':limits})
    agent.refine_times=1
    metadata={'model':agent.model,'folder':str(folder),'limits':limits.to_dict(),
              'billing_rate_reference_cny_per_million':[.8,2.7],
              'billing_reference_url':'https://help.aliyun.com/en/model-studio/qwen3-8-flash',
              'notice':'Live provider, original GUI and Harness; no mocks. Use at most three paid actions before reviewing session usage.'}
    (folder/'session.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps({'session':str(folder),'model':agent.model}),flush=True)
    try:
        Application(agent=agent).mainloop()
    finally:
        agent.close()


if __name__=='__main__':
    main()
