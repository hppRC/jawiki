# wikipedia-ja

```
mkdir -p data/jawiki
wget -c https://dumps.wikimedia.org/other/enterprise_html/runs/20240101/jawiki-NS0-20240101-ENTERPRISE-HTML.json.tar.gz
tar -zxvf jawiki-NS0-20240101-ENTERPRISE-HTML.json.tar.gz -C data/jawiki
python main.py
```