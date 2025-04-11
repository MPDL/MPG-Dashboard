import pandas as pd
from collections import Counter

df = pd.read_csv("publisher.csv")

publisher_list = df["publisher"]


publisher_list = [publisher for publisher in publisher_list if isinstance(publisher, str)]

counter = Counter(publisher_list)
print(counter)
