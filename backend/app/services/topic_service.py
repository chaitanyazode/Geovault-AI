"""
GeoVault AI - Topic Analysis & Word Cloud Service
Performs deterministic, permission-scoped topic discovery, TF-IDF keyword extraction,
topic clustering (K-Means), and WordCloud image generation.
Strictly adheres to AUTHORIZATION BEFORE RETRIEVAL.
"""

import os
import re
import time
from typing import List, Dict, Any, Optional, Tuple, Set, NamedTuple
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, text
from fastapi import HTTPException, status
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from wordcloud import WordCloud

from app.security.context import UserContext, AuthorizedScope
from app.security.service import AuthorizationService
from app.security.clearance import get_clearance_rank, CLEARANCE_RANKS


class WordCloudResult(NamedTuple):
    image_url: Optional[str]
    image_path: Optional[str]

    @property
    def wordcloud_url(self) -> Optional[str]:
        return self.image_url

    @property
    def wordcloud_path(self) -> Optional[str]:
        return self.image_path

from app.models.knowledge import Document, DocumentChunk
from app.schemas.topics import (
    KeywordItem,
    TopicCluster,
    TopicAnalysisRequest,
    TopicAnalysisResponse,
    KeywordExtractionResponse,
    WordCloudResponse,
)

# Base storage path for generated word clouds
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORDCLOUD_DIR = os.path.join(BASE_DIR, "data", "generated", "wordclouds")
os.makedirs(WORDCLOUD_DIR, exist_ok=True)

# Custom domain stopwords to filter noisy procedural text
DOMAIN_STOPWORDS = {
    "page", "table", "fig", "figure", "report", "dated", "annexure", "section",
    "ltd", "limited", "cmpdi", "cil", "sub", "ref", "para", "govt", "india",
    "coal", "mine", "mining", "total", "annual", "monthly", "year", "shall",
    "per", "also", "may", "one", "two", "three", "date", "no", "nos", "etc",
    "within", "above", "below", "due", "given", "noted", "level", "area",
}


class TopicAnalysisService:
    """
    Topic Intelligence & Word Cloud Service.
    Enforces authorization pre-filtering on document chunks before text analysis.
    """

    _CACHE: Dict[str, Tuple[float, TopicAnalysisResponse]] = {}
    CACHE_TTL_SECONDS = 300  # 5 minutes

    CANONICAL_NAME_MAP: Dict[str, str] = {
        "GV001": "GEVRA",
        "GEVRA": "GEVRA",
        "DEOM-01": "GEVRA",
        "M-GEVRA": "GEVRA",
        "GV002": "KUSMUNDA",
        "KUSMUNDA": "KUSMUNDA",
        "KNUG-02": "KUSMUNDA",
        "M-KUSMUNDA": "KUSMUNDA",
        "GV003": "DIPKA",
        "DIPKA": "DIPKA",
        "M-DIPKA": "DIPKA",
        "GV004": "NIGAHI",
        "NIGAHI": "NIGAHI",
        "M-NIGAHI": "NIGAHI",
        "GV005": "DUDHICHUA",
        "DUDHICHUA": "DUDHICHUA",
        "SSOP-03": "DUDHICHUA",
        "M-DUDHICHUA": "DUDHICHUA",
    }

    @classmethod
    def clear_cache(cls) -> None:
        """Clears in-memory topic analysis cache."""
        cls._CACHE.clear()

    @classmethod
    def get_scoped_chunks(
        cls,
        db: Session,
        scope: AuthorizedScope,
        mine_code: Optional[str] = None,
        department: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[DocumentChunk]:
        """
        Retrieves document chunks matching user's authorized scope and optional filters.
        Enforces mine, department, and clearance scopes inside PostgreSQL BEFORE retrieval.
        """
        # 1. Mine authorization verification
        if mine_code:
            if not scope.is_mine_permitted(mine_code):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: User '{scope.user_id}' is not authorized to access topics for mine '{mine_code}'.",
                )

        # 2. Build pre-filtering SQL clauses
        where_conditions = [DocumentChunk.chunk_text.isnot(None)]

        # Mine boundary
        if mine_code:
            aliases = AuthorizedScope.MINE_ALIAS_SETS.get(mine_code.upper(), {mine_code})
            where_conditions.append(or_(DocumentChunk.mine_code.in_(list(aliases)), DocumentChunk.mine_code.is_(None)))
        elif scope.allowed_mines is not None:
            if len(scope.allowed_mines) == 0:
                return []
            all_permitted_aliases: Set[str] = set()
            for m in scope.allowed_mines:
                all_permitted_aliases.update(AuthorizedScope.MINE_ALIAS_SETS.get(m.upper(), {m}))
            where_conditions.append(
                or_(DocumentChunk.mine_code.in_(list(all_permitted_aliases)), DocumentChunk.mine_code.is_(None))
            )

        # Department boundary
        if department:
            if scope.allowed_departments is not None and department not in scope.allowed_departments:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: User '{scope.user_id}' lacks clearance for department '{department}'.",
                )
            where_conditions.append(DocumentChunk.department == department)
        elif scope.allowed_departments is not None and len(scope.allowed_departments) > 0:
            where_conditions.append(
                or_(DocumentChunk.department.in_(list(scope.allowed_departments)), DocumentChunk.department.is_(None))
            )

        # Clearance boundary
        user_rank = get_clearance_rank(scope.max_clearance)
        allowed_classifications = [k.value for k, v in CLEARANCE_RANKS.items() if v <= user_rank]
        where_conditions.append(DocumentChunk.classification.in_(allowed_classifications))

        # Year filter (via joined Document)
        stmt = select(DocumentChunk).join(Document, DocumentChunk.document_id == Document.document_id)
        if year:
            where_conditions.append(Document.year == year)

        stmt = stmt.where(and_(*where_conditions)).order_by(DocumentChunk.chunk_id)
        return list(db.scalars(stmt).all())

    @classmethod
    def clean_text(cls, text_content: str) -> str:
        """Removes non-alphanumeric noise while preserving domain phrases."""
        text_clean = re.sub(r"[^a-zA-Z\s\-]", " ", text_content)
        tokens = [t.lower() for t in text_clean.split() if len(t) > 2 and t.lower() not in DOMAIN_STOPWORDS]
        return " ".join(tokens)

    @classmethod
    def extract_keywords_tfidf(
        cls,
        chunks: List[DocumentChunk],
        max_keywords: int = 30,
        top_n: Optional[int] = None,
    ) -> List[KeywordItem]:
        """
        Extracts dominant keywords and bigrams using TF-IDF weights and corpus frequencies.
        """
        limit = top_n if top_n is not None else max_keywords
        if not chunks:
            return []

        corpus = [cls.clean_text(c.chunk_text) for c in chunks if c.chunk_text]
        # Filter empty texts
        corpus = [doc for doc in corpus if len(doc.split()) >= 3]
        if not corpus:
            return []

        # TF-IDF Vectorizer
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.90 if len(corpus) > 3 else 1.0,
            max_features=150,
            stop_words="english",
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            return []

        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = tfidf_matrix.max(axis=0).toarray()[0]

        # Raw term frequency counting across corpus
        word_counts: Counter = Counter()
        doc_counts: Dict[str, Set[str]] = {}

        for chunk, doc in zip(chunks, corpus):
            words = doc.split()
            word_counts.update(words)
            # Bigrams
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
            word_counts.update(bigrams)

            for term in set(words + bigrams):
                if term not in doc_counts:
                    doc_counts[term] = set()
                doc_counts[term].add(chunk.document_id)

        keyword_items: List[KeywordItem] = []
        for i, term in enumerate(feature_names):
            # Exclude short or stopword tokens
            if len(term) < 3 or term in DOMAIN_STOPWORDS:
                continue
            freq = word_counts.get(term, 1)
            score = round(float(tfidf_scores[i]), 4)
            d_count = len(doc_counts.get(term, set()))
            keyword_items.append(
                KeywordItem(
                    keyword=term,
                    frequency=freq,
                    tfidf_score=score,
                    document_count=d_count or 1,
                )
            )

        # Sort primarily by TF-IDF score and frequency
        keyword_items.sort(key=lambda x: (x.tfidf_score * 0.6 + (min(x.frequency, 50) / 50.0) * 0.4), reverse=True)
        return keyword_items[:limit]

    @classmethod
    def cluster_topics(
        cls,
        chunks: List[DocumentChunk],
        num_clusters: int = 4,
        num_topics: Optional[int] = None,
    ) -> List[TopicCluster]:
        """
        Clusters document chunks into thematic topic groups using K-Means.
        Identifies top terms and derives grounded topic titles and descriptions.
        """
        k_target = num_topics if num_topics is not None else num_clusters
        if not chunks:
            return []

        corpus = [cls.clean_text(c.chunk_text) for c in chunks if c.chunk_text]
        clean_pairs = [(c, doc) for c, doc in zip(chunks, corpus) if len(doc.split()) >= 3]

        if not clean_pairs:
            return []

        valid_chunks, valid_corpus = zip(*clean_pairs)
        n_samples = len(valid_corpus)

        # Constrain clusters to sample count
        k = min(k_target, max(1, n_samples // 2)) if n_samples > 3 else 1


        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95 if n_samples > 4 else 1.0,
            max_features=80,
            stop_words="english",
        )

        try:
            X = vectorizer.fit_transform(valid_corpus)
            feature_names = vectorizer.get_feature_names_out()

            if k > 1 and n_samples >= k:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
                labels = kmeans.fit_predict(X)
                centers = kmeans.cluster_centers_
            else:
                labels = [0] * n_samples
                centers = [X.mean(axis=0).A1]

        except Exception:
            return cls._fallback_clusters(valid_chunks)

        topic_clusters: List[TopicCluster] = []
        for cluster_idx in range(k):
            # Find chunks belonging to this cluster
            c_chunks = [valid_chunks[i] for i, lbl in enumerate(labels) if lbl == cluster_idx]
            if not c_chunks:
                continue

            # Top keywords from centroid
            center_scores = centers[cluster_idx]
            top_indices = center_scores.argsort()[::-1][:6]
            top_words = [feature_names[i] for i in top_indices if len(feature_names[i]) > 2]
            mines_in_cluster = sorted(list({cls.CANONICAL_NAME_MAP.get(c.mine_code, c.mine_code) for c in c_chunks if c.mine_code}))

            # Generate grounded cluster title
            title = cls._synthesize_cluster_title(top_words, c_chunks)
            desc = f"Thematic cluster centered on {', '.join(top_words[:4])} across {len(c_chunks)} document section(s)."
            quotes = [c.chunk_text[:120].strip() + "..." for c in c_chunks[:2] if c.chunk_text]

            topic_clusters.append(
                TopicCluster(
                    topic_id=f"TOPIC-{cluster_idx + 1:02d}",
                    title=title,
                    top_keywords=top_words,
                    document_chunk_count=len(c_chunks),
                    mines_covered=mines_in_cluster,
                    description=desc,
                    representative_quotes=quotes,
                )
            )

        return topic_clusters

    @classmethod
    def _synthesize_cluster_title(cls, top_words: List[str], chunks: List[DocumentChunk]) -> str:
        """Determines domain-specific topic title based on cluster features."""
        terms = set(" ".join(top_words).lower().split())
        depts = {c.department for c in chunks if c.department}

        if terms & {"fault", "strata", "geology", "geotechnical", "rqd", "formation", "lithology", "bedrock"}:
            return "Geotechnical Strata & Fault Structure"
        if terms & {"water", "ingress", "seepage", "monsoon", "drainage", "sump", "precipitation", "flooding"}:
            return "Hydrogeology & Monsoon Drainage Issues"
        if terms & {"dumper", "shovel", "equipment", "breakdown", "downtime", "haul", "transport", "logistics"}:
            return "Heavy Earth Moving Machinery & Haul Logistics"
        if terms & {"ash", "gcv", "moisture", "calorific", "grade", "quality", "sampling"}:
            return "Coal Quality & Seam Characteristics"
        if terms & {"statutory", "safety", "inspection", "audit", "violation", "dgms", "compliance"}:
            return "Statutory Safety & Compliance Audits"

        if "Geology" in depts:
            return "Geological Formations & Overburden Characteristics"
        if "Transportation" in depts:
            return "Logistics Operations & Dispatch Flow"
        if "Safety" in depts:
            return "Statutory Safety Observations & Field Audits"

        clean_lead = [w.title() for w in top_words[:2] if len(w) > 3]
        return f"{' & '.join(clean_lead)} Operations" if clean_lead else "General Mining Operations"

    @classmethod
    def _fallback_clusters(cls, chunks: List[DocumentChunk]) -> List[TopicCluster]:
        """Provides deterministic fallback clusters when sample size is minimal."""
        mines = sorted(list({cls.CANONICAL_NAME_MAP.get(c.mine_code, c.mine_code) for c in chunks if c.mine_code}))
        quotes = [c.chunk_text[:120].strip() + "..." for c in chunks[:2] if c.chunk_text]
        return [
            TopicCluster(
                topic_id="TOPIC-01",
                title="Operational & Geological Documentation",
                top_keywords=["operations", "strata", "production"],
                document_chunk_count=len(chunks),
                mines_covered=mines,
                description=f"Unified document knowledge cluster spanning {len(chunks)} verified record(s).",
                representative_quotes=quotes,
            )
        ]


    @classmethod
    def generate_wordcloud_image(
        cls,
        keywords: List[KeywordItem],
        file_identifier: str,
    ) -> WordCloudResult:
        """
        Renders a high-resolution WordCloud image and saves it to data/generated/wordclouds/.
        Returns WordCloudResult (can be unpacked as tuple (image_url, image_path) or accessed by attribute).
        """
        if not keywords:
            return WordCloudResult(None, None)

        freq_dict = {k.keyword: max(1, k.frequency) for k in keywords}

        try:
            wc = WordCloud(
                width=800,
                height=400,
                background_color="white",
                colormap="viridis",
                max_words=60,
                contour_width=1,
                contour_color="#1E3A8A",
            )
            wc.generate_from_frequencies(freq_dict)

            filename = f"wordcloud_{file_identifier}.png"
            file_path = os.path.join(WORDCLOUD_DIR, filename)
            wc.to_file(file_path)

            relative_url = f"/api/v1/topics/wordcloud/image/{filename}"
            return WordCloudResult(relative_url, file_path)

        except Exception as e:
            print(f"[!] WordCloud rendering error: {e}")
            return WordCloudResult(None, None)

    @classmethod
    def analyze_topics(
        cls,
        db: Session,
        scope: Any,
        req: Optional[TopicAnalysisRequest] = None,
        mine_code: Optional[str] = None,
        department: Optional[str] = None,
        year: Optional[int] = None,
        max_keywords: Optional[int] = None,
        num_clusters: Optional[int] = None,
        num_topics: Optional[int] = None,
        top_keywords: Optional[int] = None,
        generate_wordcloud: bool = True,
        **kwargs,
    ) -> TopicAnalysisResponse:
        """
        Complete topic discovery workflow: Scoped Chunk Retrieval -> TF-IDF Keywords ->
        K-Means Clustering -> WordCloud Generation -> In-memory Caching.
        """
        t_start = time.perf_counter()

        # Resolve scope from UserContext or user_id string if needed
        if isinstance(scope, UserContext):
            resolved_scope = AuthorizationService.get_authorized_scope(scope)
        elif isinstance(scope, AuthorizedScope):
            resolved_scope = scope
        else:
            user_ctx = AuthorizationService.resolve_user_context(db, str(scope))
            resolved_scope = AuthorizationService.get_authorized_scope(user_ctx)

        # Build request model if kwargs supplied
        if req is None:
            final_max_kw = top_keywords if top_keywords is not None else (max_keywords or 25)
            final_clusters = num_topics if num_topics is not None else (num_clusters or 4)
            req = TopicAnalysisRequest(
                mine_code=mine_code,
                department=department,
                year=year,
                max_keywords=final_max_kw,
                num_clusters=final_clusters,
                generate_wordcloud=generate_wordcloud,
            )

        # Cache key construction
        allowed_mines_key = tuple(sorted(list(resolved_scope.allowed_mines))) if resolved_scope.allowed_mines is not None else "ALL"
        cache_key = f"{resolved_scope.user_id}:{allowed_mines_key}:{resolved_scope.max_clearance}:{req.mine_code}:{req.department}:{req.year}:{req.num_clusters}"

        # Check cache
        if cache_key in cls._CACHE:
            ts, cached_res = cls._CACHE[cache_key]
            if time.time() - ts < cls.CACHE_TTL_SECONDS:
                return cached_res

        # 1. Scoped Chunk Retrieval
        chunks = cls.get_scoped_chunks(
            db=db,
            scope=resolved_scope,
            mine_code=req.mine_code,
            department=req.department,
            year=req.year,
        )


        scope_dict = resolved_scope.to_dict()
        scope_dict["mine_filter"] = req.mine_code
        scope_dict["department_filter"] = req.department
        scope_dict["year_filter"] = req.year
        scope_dict["user_mines"] = scope_dict["allowed_mines"]

        data_gaps: List[str] = []
        if not chunks:
            desc = "No authorized document chunks found"
            if req.mine_code:
                desc += f" for mine '{req.mine_code}'"
            if req.department:
                desc += f" in department '{req.department}'"
            if req.year:
                desc += f" for year {req.year}"
            data_gaps.append(desc)

            res = TopicAnalysisResponse(
                topics=[],
                keywords=[],
                total_chunks_analyzed=0,
                total_documents_analyzed=0,
                scope_applied=scope_dict,
                wordcloud_url=None,
                wordcloud_path=None,
                data_gaps=data_gaps,
                processing_time_ms=round((time.perf_counter() - t_start) * 1000, 2),
            )
            cls._CACHE[cache_key] = (time.time(), res)
            return res

        # 2. Extract Keywords via TF-IDF
        keywords = cls.extract_keywords_tfidf(chunks, max_keywords=req.max_keywords)

        # 3. Cluster Topics
        topics = cls.cluster_topics(chunks, num_clusters=req.num_clusters)

        # 4. Generate WordCloud if requested
        wc_url = None
        wc_path = None
        if req.generate_wordcloud and keywords:
            file_id = f"{req.mine_code or 'ALL'}_{req.department or 'ALL'}_{req.year or 'ALL'}_{resolved_scope.user_id}_{int(time.time())}"
            wc_url, wc_path = cls.generate_wordcloud_image(keywords, file_id)

        distinct_docs = len({c.document_id for c in chunks})
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

        response = TopicAnalysisResponse(
            topics=topics,
            keywords=keywords,
            total_chunks_analyzed=len(chunks),
            total_documents_analyzed=distinct_docs,
            scope_applied=scope_dict,
            wordcloud_url=wc_url,
            wordcloud_path=wc_path,
            data_gaps=data_gaps,
            processing_time_ms=elapsed_ms,
        )

        # Populate cache
        cls._CACHE[cache_key] = (time.time(), response)
        return response

