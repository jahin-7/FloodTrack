import argparse,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from floodtrack.reporting import answer_question
p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--question',required=True)
a=p.parse_args();print(answer_question(a.run,a.question))
