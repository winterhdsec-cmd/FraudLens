import os, tempfile, json
# 构造一个小 AMLSim 目录（含回流环 A1->A2->A3->A1）验证 --amlsim 管线
d = tempfile.mkdtemp()
with open(os.path.join(d, "transactions.csv"), "w", encoding="utf-8") as f:
    f.write("TX_ID,TIMESTAMP,SENDER_ACCOUNT_ID,RECEIVER_ACCOUNT_ID,AMOUNT,TX_TYPE\n")
    f.write("1,100,A1,A2,1000,1\n2,200,A2,A3,900,1\n3,300,A3,A1,800,1\n4,400,A1,A9,500,1\n")
with open(os.path.join(d, "accounts.csv"), "w", encoding="utf-8") as f:
    f.write("ACCOUNT_ID,ACCOUNT_TYPE\nA1,1\nA2,2\nA3,3\nA9,4\n")
import subprocess, sys
r = subprocess.run([sys.executable, "/app/scripts/eval_business.py", "--amlsim", d],
                   capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "/app"})
print(r.stdout)
print("STDERR_TAIL:", r.stderr[-500:] if r.stderr else "")
print("RETURN", r.returncode)
