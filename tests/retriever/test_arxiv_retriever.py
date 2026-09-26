"""Tests for ArxivRetriever."""

from zotero_arxiv_daily.retriever.arxiv_retriever import ArxivRetriever


def test_arxiv_retriever(config, mock_feedparser, monkeypatch):
    monkeypatch.setattr("zotero_arxiv_daily.retriever.base.sleep", lambda _: None)

    retriever = ArxivRetriever(config)
    papers = retriever.retrieve_papers()

    # 示例 feed 里只有 2 条 announce_type == "new"
    assert len(papers) == 2
    assert set(p.title for p in papers) == {
        "Neural Architecture Search for Efficient Transformers",
        "Reward Shaping in Multi-Agent Reinforcement Learning",
    }


def test_convert_to_paper_parses_feed_entry(config, mock_feedparser):
    retriever = ArxivRetriever(config)
    # 取第一条（cross 类型）条目，直接验证字段解析（不走 announce_type 过滤）
    entry = mock_feedparser.entries[0]
    paper = retriever.convert_to_paper(entry)

    assert paper.title.startswith("ALIGN:")
    assert paper.authors == ["Chunhua Liu", "Kabir Manandhar Shrestha", "Sukai Huang"]
    assert paper.abstract.startswith("As large language models")
    assert paper.url == "https://arxiv.org/abs/2508.13426"
    assert paper.pdf_url == "https://arxiv.org/pdf/2508.13426"
    assert paper.full_text is None
