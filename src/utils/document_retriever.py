"""
内部ドキュメント検索用RAGクラス
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document

logger = logging.getLogger(__name__)

class DocumentRetriever:
    """内部ドキュメント検索用RAGクラス"""
    
    def __init__(
        self,
        doc_dir: str = "internalDoc",
        chunk_size: int = 400,
        chunk_overlap: int = 100,
        embedding_model: str = "cl-tohoku/bert-base-japanese-whole-word-masking",
        persist_directory: str = "artifact/chroma_db"
    ):
        """
        初期化
        
        Args:
            doc_dir: ドキュメントディレクトリ
            chunk_size: チャンクサイズ
            chunk_overlap: チャンクのオーバーラップ
            embedding_model: 埋め込みモデル
            persist_directory: ベクトルDBの保存ディレクトリ
        """
        self.doc_dir = Path(doc_dir).resolve()  # 絶対パスに変換
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.persist_directory = Path(persist_directory)
        
        # テキスト分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["##", "-", "●", "\n\n", "\n", "。", "、", " ", ""]
        )
        
        # 埋め込みモデル
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # ベクトルストア
        self.vectorstore = None
        
    def load_documents(self) -> List[Document]:
        """ドキュメントの読み込み"""
        if not self.doc_dir.exists():
            logger.warning(f"ドキュメントディレクトリが存在しません: {self.doc_dir}")
            return []
        
        # ローダーの設定
        loaders = {
            "*.txt": lambda path: TextLoader(
                str(path),
                encoding='utf-8',  # 文字コードを明示的に指定
                autodetect_encoding=True  # 自動検出も有効化
            ),
            "*.md": UnstructuredMarkdownLoader
        }
        
        documents = []
        for pattern, loader_class in loaders.items():
            try:
                # パターンに一致するファイルを検索
                files = list(self.doc_dir.glob(pattern))
                if not files:
                    logger.info(f"{pattern}に一致するファイルが見つかりません")
                    continue
                
                # 各ファイルを読み込み
                for file_path in files:
                    try:
                        if pattern == "*.txt":
                            loader = loader_class(file_path)
                        else:
                            loader = loader_class(str(file_path))
                        
                        docs = loader.load()
                        documents.extend(docs)
                        logger.info(f"{file_path.name}から{len(docs)}件のドキュメントを読み込みました")
                    except Exception as e:
                        logger.error(f"{file_path.name}の読み込み中にエラー: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"{pattern}の読み込み中にエラー: {str(e)}")
        
        if not documents:
            logger.warning("読み込めるドキュメントがありません")
        
        return documents
    
    def create_index(self, force_recreate: bool = False) -> None:
        """
        インデックスの作成
        
        Args:
            force_recreate: 既存のインデックスを強制的に再作成するか
        """
        # 既存のインデックスをチェック
        if not force_recreate and self.persist_directory.exists():
            try:
                self.vectorstore = FAISS.load_local(
                    folder_path=str(self.persist_directory),
                    embeddings=self.embeddings
                )
                logger.info("既存のインデックスを読み込みました")
                return
            except Exception as e:
                logger.warning(f"既存のインデックスの読み込みに失敗: {str(e)}")
        
        # ドキュメントの読み込み
        documents = self.load_documents()
        if not documents:
            logger.warning("インデックス作成に必要なドキュメントがありません")
            return
        
        # テキストの分割
        splits = self.text_splitter.split_documents(documents)
        logger.info(f"ドキュメントを{len(splits)}個のチャンクに分割しました")
        
        # ベクトルストアの作成
        self.vectorstore = FAISS.from_documents(
            documents=splits,
            embedding=self.embeddings
        )
        
        # インデックスの保存
        self.vectorstore.save_local(str(self.persist_directory))
        logger.info(f"インデックスを作成し、{self.persist_directory}に保存しました")
    
    def search(
        self,
        query: str,
        k: int = 3,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        類似ドキュメントの検索（クエリ拡張・閾値段階調整）
        """
        if not self.vectorstore:
            logger.warning("インデックスが作成されていません")
            return []
        # クエリ拡張
        synonyms = ["職歴", "経歴", "勤務先", "キャリア", "仕事", "職務経歴"]
        expanded_query = query + " " + " ".join([s for s in synonyms if s not in query])
        thresholds = [score_threshold, 0.3, 0.1]
        for th in thresholds:
            try:
                docs_and_scores = self.vectorstore.similarity_search_with_score(
                    expanded_query,
                    k=k
                )
                results = []
                for doc, score in docs_and_scores:
                    if score < th:
                        continue
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": float(score),
                        "source": doc.metadata.get("source", "unknown")
                    })
                logger.info(f"検索結果: {len(results)}件（閾値: {th}）")
                if results:
                    return results
            except Exception as e:
                logger.error(f"検索中にエラー: {str(e)}")
        return []
    
    def get_document_info(self) -> Dict[str, Any]:
        """ドキュメント情報の取得（FAISS互換対応）"""
        if not self.vectorstore:
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "last_updated": None
            }
        try:
            # docstore._dictは{doc_id: Document}のdict
            doc_dict = getattr(self.vectorstore, 'docstore', None)
            if doc_dict and hasattr(doc_dict, '_dict'):
                all_docs = list(doc_dict._dict.values())
                total_chunks = len(all_docs)
                sources = set()
                for doc in all_docs:
                    if hasattr(doc, 'metadata') and 'source' in doc.metadata:
                        sources.add(doc.metadata['source'])
                return {
                    "total_documents": len(sources),
                    "total_chunks": total_chunks,
                    "last_updated": datetime.fromtimestamp(
                        os.path.getmtime(self.persist_directory)
                    ).isoformat() if self.persist_directory.exists() else None
                }
            else:
                return {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "last_updated": None,
                    "error": "docstore未対応"
                }
        except Exception as e:
            logger.error(f"ドキュメント情報の取得中にエラー: {str(e)}")
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "last_updated": None,
                "error": str(e)
            } 