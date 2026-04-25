import pandas as pd

def get_games() -> pd.DataFrame:
    csv_url = "https://docs.google.com/spreadsheets/d/1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/export?format=csv&gid=0"
    df = pd.read_csv(csv_url)
    csv_url = "https://docs.google.com/spreadsheets/d/1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/export?format=csv&gid=597170352"
    df2 = pd.read_csv(csv_url)
    csv_url = "https://docs.google.com/spreadsheets/d/1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/export?format=csv&gid=223751105"
    df3 = pd.read_csv(csv_url)
    return df, df2, df3

