from .base import BaseRetriever, register_retriever
from ..protocol import Paper
import feedparser
from loguru import logger


@register_retriever("arxiv")
class ArxivRetriever(BaseRetriever):
    def __init__(self, config):
        super().__init__(config)
        if self.config.source.arxiv.category is None:
            raise ValueError("category must be specified for arxiv.")

    def _retrieve_raw_papers(self) -> list:
        query = '+'.join(self.config.source.arxiv.category)
        include_cross_list = self.config.source.arxiv.get("include_cross_list", False)
        # 直接解析 arXiv RSS feed（已含标题/摘要/作者等全部元数据），
        # 不再调用 export.arxiv.org API —— 其会从 GitHub Actions 机房 IP 返回 HTTP 406，
        # 导致每天 0 篇论文、只发“No Papers Today”空邮件。
        feed = feedparser.parse(f"https://rss.arxiv.org/atom/{query}")
        if 'Feed error for query' in feed.feed.title:
            raise Exception(f"Invalid ARXIV_QUERY: {query}.")
        allowed_announce_types = {"new", "cross"} if include_cross_list else {"new"}
        entries = [
            e for e in feed.entries
            if e.get("arxiv_announce_type", "new") in allowed_announce_types
        ]
        if self.config.executor.debug:
            entries = entries[:10]
        return entries

    def convert_to_paper(self, entry) -> Paper:
        # entry: feedparser.FeedParserDict（RSS 里的一条 <entry>）
        abs_url = None
        for link in entry.get("links", []):
            if link.get("rel") == "alternate":
                abs_url = link.get("href")
                break
        if abs_url is None:
            abs_url = entry.get("link")

        if abs_url is None:
            paper_id = (entry.get("id") or "").removeprefix("oai:arXiv.org:")
            abs_url = f"https://arxiv.org/abs/{paper_id.split('v', 1)[0]}"

        # 作者在 <dc:creator> 里，是逗号分隔的一串
        author_str = entry.get("author", "")
        authors = [a.strip() for a in author_str.split(",") if a.strip()]

        # <summary> 形如 "arXiv:2508.13426v1 Announce Type: new \nAbstract: ..."
        summary = entry.get("summary", "")
        if "Abstract:" in summary:
            abstract = summary.split("Abstract:", 1)[-1].strip()
        else:
            abstract = summary.strip()

        return Paper(
            source=self.name,
            title=(entry.get("title") or "").strip(),
            authors=authors,
            abstract=abstract,
            url=abs_url,
            pdf_url=abs_url.replace("/abs/", "/pdf/") if abs_url else None,
            # 排序只用摘要，不再下载全文：省下每次 ~2 小时的串行全文解析，
            # 也规避 arxiv.org 全文接口对机房 IP 的拦截。
            full_text=None,
        )
