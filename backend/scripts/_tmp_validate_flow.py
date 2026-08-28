import tempfile, os
from gnn.adapters.fund_flow_io import (
    parse_fund_flow_csv, parse_fund_flow_file, amlsim_to_accounts_tx
)

# 1) English headers
csv_en = ("SENDER_ACCOUNT_ID,RECEIVER_ACCOUNT_ID,AMOUNT,TIMESTAMP\n"
          "62280001,62170002,12000.5,2026-01-10 09:00\n"
          "62170002,62280003,11000,2026-01-11 10:00\n")
tx, stats = parse_fund_flow_csv(csv_en)
print("EN_OK n=", len(tx), "stats=", stats)
print("  sample=", tx[0])

# 2) Chinese headers (common bank export)
csv_cn = ("付款账号,收款账号,金额,交易时间\n"
          "aaa111,bbb222,5000,2026-02-01\n"
          "bbb222,ccc333,4800,2026-02-02\n")
tx2, s2 = parse_fund_flow_csv(csv_cn)
print("CN_OK n=", len(tx2), "stats=", s2)

# 3) missing account columns -> must raise
try:
    parse_fund_flow_csv("foo,bar\n1,2\n")
    print("ERR: should have raised")
except Exception as e:
    print("MISSING_COL_OK raised:", str(e)[:50])

# 4) AMLSim wrapper (synthetic small dir)
d = tempfile.mkdtemp()
with open(os.path.join(d, "transactions.csv"), "w", encoding="utf-8") as f:
    f.write("TX_ID,TIMESTAMP,SENDER_ACCOUNT_ID,RECEIVER_ACCOUNT_ID,AMOUNT,TX_TYPE\n")
    f.write("1,100,A1,A2,1000,1\n2,200,A2,A3,900,1\n3,300,A3,A1,800,1\n")
with open(os.path.join(d, "accounts.csv"), "w", encoding="utf-8") as f:
    f.write("ACCOUNT_ID,ACCOUNT_TYPE\nA1,1\nA2,2\nA3,3\n")
atx, astats = amlsim_to_accounts_tx(d)
print("AMLSIM_WRAP_OK n=", len(atx), "stats=", astats)
print("  sample=", atx[0])

# 5) model import
from database.models import ImportedFundFlow
print("MODEL_OK table=", ImportedFundFlow.__tablename__)
