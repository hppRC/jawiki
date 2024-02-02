import json
import pdb
import re
import unicodedata
from pathlib import Path

import datasets as ds
from bs4 import BeautifulSoup

paths = []
for path in Path("data/jawiki").glob("jawiki_namespace_0_*.ndjson"):
    [idx] = re.findall(r"jawiki_namespace_0_(\d+).ndjson", path.name)
    paths.append((int(idx), path))
paths = [path for _, path in sorted(paths, key=lambda x: x[0])]


def process(example: dict):
    abstract = example.get("abstract")
    templates: list[str] = [t["name"] for t in example.get("templates", [])]

    is_disambiguation_page = any("Template:Dmbox" in template for template in templates) or any(
        "Template:Aimai" in template for template in templates
    )
    is_sexual_page = any("Template:性的" in template for template in templates)
    is_violent_page = any("Template:暴力的" in template for template in templates)

    return {
        "identifier": example["identifier"],
        "title": example["name"],
        "abstract": abstract,
        "html": example["article_body"].get("html"),
        "wikitext": example["article_body"].get("wikitext"),
        "url": example["url"],
        "date_created": example.get("date_created"),
        "date_modified": example.get("date_modified"),
        "is_disambiguation_page": is_disambiguation_page,
        "is_sexual_page": is_sexual_page,
        "is_violent_page": is_violent_page,
        "templates": templates,
    }


def gen():
    for path in paths:
        with open(path) as f:
            for line in f:
                yield process(json.loads(line))


dataset = ds.Dataset.from_generator(gen, cache_dir="./data")
dataset = dataset.filter(lambda x: x["html"] is not None)

SECTIONS_TO_IGNORE = ["脚注", "出典", "参考文献", "関連項目", "外部リンク"]
TAGS_TO_REMOVE = ["table"]
INNER_TAGS_TO_REMOVE = ["sup"]
TAGS_TO_EXTRACT = ["p"]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())
    text = "".join(char for char in text if char.isprintable())
    text = text.strip()
    return text


def process(example: dict):
    soup = BeautifulSoup(example["html"], features="lxml")
    section_title = ""
    section = soup.find(["section"])

    paragraph_id = 0
    paragraphs = []

    while section:
        if section.h2 is not None:
            section_title = section.h2.text

        for tag in section.find_all(TAGS_TO_REMOVE):
            tag.clear()

        for tag in section.find_all(TAGS_TO_EXTRACT):
            for inner_tag in tag.find_all(INNER_TAGS_TO_REMOVE):
                inner_tag.clear()

            paragraph_text = normalize_text(tag.text)

            if section_title in SECTIONS_TO_IGNORE:
                continue

            paragraphs.append(
                {
                    "title": section_title,
                    "text": paragraph_text,
                    "tag": tag.name,
                    "paragraph_id": paragraph_id,
                }
            )
            paragraph_id += 1

        section = section.find_next_sibling(["section"])

    return {"paragraphs": paragraphs}


dataset = dataset.map(process, remove_columns=["html"])


def process(example: dict):
    return {
        "text": "\n".join(paragraph["text"] for paragraph in example["paragraphs"]),
    }


dataset = dataset.map(process)

dataset = dataset.sort("identifier")
dataset = dataset.select_columns(
    [
        "identifier",
        "title",
        "text",
        "paragraphs",
        "abstract",
        "wikitext",
        "date_created",
        "date_modified",
        "is_disambiguation_page",
        "is_sexual_page",
        "is_violent_page",
        "templates",
        "url",
    ]
)
dataset = dataset.rename_column("identifier", "id")

dataset.push_to_hub("hpprc/jawiki", max_shard_size="1GB")

pdb.set_trace()
