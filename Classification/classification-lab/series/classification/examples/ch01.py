import pandas as pd

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int)          # 1 = the customer subscribed
print(df.shape)
print(f"{y.mean():.1%} of calls ended in a subscription")

# Which simple facts already move the needle?
for col in ["contact", "poutcome"]:
    rate = y.groupby(df[col]).agg(["mean", "size"]).round(3)
    print(rate, end="\n\n")

# Baseline 1: predict "no" for everyone
print(f"accuracy of always saying no: {(y == 0).mean():.3f}")

# Baseline 2: call only people who said yes to a previous campaign
rule = (df["poutcome"] == "success")
tp = int((rule & (y == 1)).sum())
print(f"rule calls {rule.sum()} people, {tp} subscribe -> precision {tp / rule.sum():.2f}, recall {tp / y.sum():.2f}")
