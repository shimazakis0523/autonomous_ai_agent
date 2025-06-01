#!/usr/bin/env python3
"""
Web検索ツール（SerpAPI使用）
詳細なトレーシング機能付き
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from serpapi import GoogleSearch
from dotenv import load_dotenv

# トレーシング機能をインポート
from ..utils.trace_logger import TraceLogger

# 環境変数の読み込み
load_dotenv()

logger = logging.getLogger(__name__)

class WebSearchTool:
    """Web検索ツール（トレーシング対応）"""
    
    def __init__(self, trace_logger: Optional[TraceLogger] = None):
        """
        初期化
        
        Args:
            trace_logger: トレーシングロガー
        """
        self.api_key = os.getenv("SERPAPI_API_KEY")
        self.trace_logger = trace_logger
        
        if not self.api_key:
            logger.warning("SERPAPI_API_KEYが設定されていません。Web検索機能は利用できません。")
    
    def search_web(self, query: str, num_results: int = 10, language: str = "ja", 
                   country: str = "jp", advanced_params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Web検索を実行
        
        Args:
            query: 検索クエリ
            num_results: 取得する結果数
            language: 検索言語
            country: 検索対象国
            advanced_params: 追加の検索パラメータ
            
        Returns:
            検索結果の辞書
        """
        if not self.api_key:
            error_result = {
                "error": "SERPAPI_API_KEYが設定されていません",
                "status": "error",
                "results": []
            }
            if self.trace_logger:
                self.trace_logger.log_custom_event(
                    "WEB_SEARCH_ERROR", 
                    "API key not configured", 
                    {"query": query, "error": "Missing API key"}
                )
            return error_result
        
        # 検索パラメータの構築
        search_params = {
            "q": query,
            "hl": language,
            "gl": country,
            "num": num_results,
            "api_key": self.api_key
        }
        
        # 追加パラメータがある場合は統合
        if advanced_params:
            search_params.update(advanced_params)
        
        # トレーシング開始
        if self.trace_logger:
            with self.trace_logger.trace_web_search(query, "Google (SerpAPI)", search_params):
                return self._execute_search(search_params, query)
        else:
            return self._execute_search(search_params, query)
    
    def _execute_search(self, search_params: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        実際の検索実行
        
        Args:
            search_params: 検索パラメータ
            query: 検索クエリ
            
        Returns:
            検索結果
        """
        try:
            logger.info(f"🔍 Web検索実行: '{query}'")
            
            # SerpAPI検索実行
            search = GoogleSearch(search_params)
            raw_results = search.get_dict()
            
            # 結果の整理
            processed_results = self._process_search_results(raw_results, query)
            
            # トレーシングロガーに結果を記録
            if self.trace_logger:
                for result in processed_results.get("results", []):
                    self.trace_logger.log_search_result(result)
            
            logger.info(f"✅ Web検索完了: {len(processed_results.get('results', []))}件の結果を取得")
            
            return processed_results
            
        except Exception as e:
            error_msg = f"Web検索エラー: {str(e)}"
            logger.error(error_msg)
            
            error_result = {
                "error": error_msg,
                "status": "error",
                "results": [],
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            
            if self.trace_logger:
                self.trace_logger.log_custom_event(
                    "WEB_SEARCH_ERROR", 
                    error_msg, 
                    {"query": query, "search_params": search_params}
                )
            
            return error_result
    
    def _process_search_results(self, raw_results: Dict, query: str) -> Dict[str, Any]:
        """
        検索結果の処理と整理
        
        Args:
            raw_results: SerpAPIからの生の結果
            query: 検索クエリ
            
        Returns:
            処理済み検索結果
        """
        processed = {
            "query": query,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "results": [],
            "metadata": {},
            "search_info": {},
            "related_searches": []
        }
        
        # メタデータの収集
        if "search_metadata" in raw_results:
            search_metadata = raw_results["search_metadata"]
            processed["metadata"] = {
                "search_id": search_metadata.get("id", ""),
                "processed_at": search_metadata.get("processed_at", ""),
                "total_time_taken": search_metadata.get("total_time_taken", 0),
                "engine_used": search_metadata.get("engine", "google")
            }
        
        # 検索情報
        if "search_information" in raw_results:
            search_info = raw_results["search_information"]
            processed["search_info"] = {
                "total_results": search_info.get("total_results", "不明"),
                "time_taken": search_info.get("time_taken_displayed", "不明"),
                "query_displayed": search_info.get("query_displayed", query)
            }
        
        # オーガニック検索結果の処理
        organic_results = raw_results.get("organic_results", [])
        for i, result in enumerate(organic_results, 1):
            processed_result = {
                "position": result.get("position", i),
                "title": result.get("title", "タイトルなし"),
                "link": result.get("link", ""),
                "displayed_link": result.get("displayed_link", ""),
                "snippet": result.get("snippet", ""),
                "date": result.get("date", ""),
                "cached_page_link": result.get("cached_page_link", ""),
                "related_pages_link": result.get("related_pages_link", ""),
                "source": "organic"
            }
            
            # リッチスニペット情報があれば追加
            if "rich_snippet" in result:
                processed_result["rich_snippet"] = result["rich_snippet"]
            
            # サイトリンクがあれば追加
            if "sitelinks" in result:
                processed_result["sitelinks"] = result["sitelinks"]
            
            processed["results"].append(processed_result)
        
        # ナレッジグラフの処理
        if "knowledge_graph" in raw_results:
            kg = raw_results["knowledge_graph"]
            knowledge_result = {
                "position": 0,  # ナレッジグラフは最上位
                "title": kg.get("title", ""),
                "type": kg.get("type", ""),
                "description": kg.get("description", ""),
                "source": "knowledge_graph",
                "source_link": kg.get("source", {}).get("link", ""),
                "thumbnail": kg.get("thumbnail", "")
            }
            
            # 詳細情報があれば追加
            if "attributes" in kg:
                knowledge_result["attributes"] = kg["attributes"]
            
            # ナレッジグラフを結果の先頭に挿入
            processed["results"].insert(0, knowledge_result)
        
        # ニュース結果の処理
        if "news_results" in raw_results:
            news_results = raw_results["news_results"]
            for news in news_results[:3]:  # 上位3件のニュース
                news_result = {
                    "title": news.get("title", ""),
                    "link": news.get("link", ""),
                    "snippet": news.get("snippet", ""),
                    "date": news.get("date", ""),
                    "source": "news",
                    "news_source": news.get("source", "")
                }
                if news.get("thumbnail"):
                    news_result["thumbnail"] = news["thumbnail"]
                
                processed["results"].append(news_result)
        
        # 関連検索の処理
        if "related_searches" in raw_results:
            related_searches = raw_results["related_searches"]
            processed["related_searches"] = [
                {
                    "query": related.get("query", ""),
                    "link": related.get("link", "")
                }
                for related in related_searches[:5]  # 上位5件
            ]
        
        # 結果数の更新
        processed["results_count"] = len(processed["results"])
        
        # 詳細ログ出力
        logger.info(f"📊 検索結果詳細:")
        logger.info(f"   • オーガニック結果: {len(organic_results)}件")
        logger.info(f"   • ナレッジグラフ: {'あり' if 'knowledge_graph' in raw_results else 'なし'}")
        logger.info(f"   • ニュース結果: {len(raw_results.get('news_results', []))}件")
        logger.info(f"   • 関連検索: {len(processed['related_searches'])}件")
        logger.info(f"   • 総結果数: {processed['results_count']}件")
        
        if processed["search_info"].get("total_results"):
            logger.info(f"   • 全体の検索結果数: {processed['search_info']['total_results']}")
        
        return processed
    
    def search_images(self, query: str, num_results: int = 10) -> Dict[str, Any]:
        """
        画像検索を実行
        
        Args:
            query: 検索クエリ
            num_results: 取得する結果数
            
        Returns:
            画像検索結果
        """
        if not self.api_key:
            return {
                "error": "SERPAPI_API_KEYが設定されていません",
                "status": "error",
                "results": []
            }
        
        search_params = {
            "q": query,
            "tbm": "isch",  # 画像検索
            "num": num_results,
            "api_key": self.api_key
        }
        
        if self.trace_logger:
            with self.trace_logger.trace_web_search(query, "Google Images (SerpAPI)", search_params):
                return self._execute_image_search(search_params, query)
        else:
            return self._execute_image_search(search_params, query)
    
    def _execute_image_search(self, search_params: Dict[str, Any], query: str) -> Dict[str, Any]:
        """画像検索の実行"""
        try:
            logger.info(f"🖼️ 画像検索実行: '{query}'")
            
            search = GoogleSearch(search_params)
            raw_results = search.get_dict()
            
            processed_results = {
                "query": query,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "results": [],
                "type": "images"
            }
            
            # 画像結果の処理
            images_results = raw_results.get("images_results", [])
            for i, image in enumerate(images_results, 1):
                image_result = {
                    "position": i,
                    "title": image.get("title", ""),
                    "link": image.get("link", ""),
                    "original": image.get("original", ""),
                    "thumbnail": image.get("thumbnail", ""),
                    "source": image.get("source", ""),
                    "source_logo": image.get("source_logo", "")
                }
                processed_results["results"].append(image_result)
                
                # トレーシングに記録
                if self.trace_logger:
                    self.trace_logger.log_search_result(image_result)
            
            processed_results["results_count"] = len(processed_results["results"])
            logger.info(f"✅ 画像検索完了: {processed_results['results_count']}件の画像を取得")
            
            return processed_results
            
        except Exception as e:
            error_msg = f"画像検索エラー: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "status": "error",
                "results": [],
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def search_news(self, query: str, num_results: int = 10, time_range: str = "d") -> Dict[str, Any]:
        """
        ニュース検索を実行
        
        Args:
            query: 検索クエリ
            num_results: 取得する結果数
            time_range: 時間範囲（d=1日、w=1週間、m=1ヶ月、y=1年）
            
        Returns:
            ニュース検索結果
        """
        if not self.api_key:
            return {
                "error": "SERPAPI_API_KEYが設定されていません",
                "status": "error",
                "results": []
            }
        
        search_params = {
            "q": query,
            "tbm": "nws",  # ニュース検索
            "num": num_results,
            "tbs": f"qdr:{time_range}",  # 時間範囲
            "api_key": self.api_key
        }
        
        if self.trace_logger:
            with self.trace_logger.trace_web_search(query, "Google News (SerpAPI)", search_params):
                return self._execute_news_search(search_params, query)
        else:
            return self._execute_news_search(search_params, query)
    
    def _execute_news_search(self, search_params: Dict[str, Any], query: str) -> Dict[str, Any]:
        """ニュース検索の実行"""
        try:
            logger.info(f"📰 ニュース検索実行: '{query}'")
            
            search = GoogleSearch(search_params)
            raw_results = search.get_dict()
            
            processed_results = {
                "query": query,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "results": [],
                "type": "news"
            }
            
            # ニュース結果の処理
            news_results = raw_results.get("news_results", [])
            for i, news in enumerate(news_results, 1):
                news_result = {
                    "position": i,
                    "title": news.get("title", ""),
                    "link": news.get("link", ""),
                    "snippet": news.get("snippet", ""),
                    "date": news.get("date", ""),
                    "source": news.get("source", ""),
                    "thumbnail": news.get("thumbnail", "")
                }
                processed_results["results"].append(news_result)
                
                # トレーシングに記録
                if self.trace_logger:
                    self.trace_logger.log_search_result(news_result)
            
            processed_results["results_count"] = len(processed_results["results"])
            logger.info(f"✅ ニュース検索完了: {processed_results['results_count']}件のニュースを取得")
            
            return processed_results
            
        except Exception as e:
            error_msg = f"ニュース検索エラー: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "status": "error",
                "results": [],
                "query": query,
                "timestamp": datetime.now().isoformat()
            } 