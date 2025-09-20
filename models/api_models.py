from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class PipelineRunRequest(BaseModel):
    """パイプライン実行APIのリクエストボディモデル"""
    start_stage: int = Field(
        default=1, 
        description=(
            "パイプラインを開始するステージ番号 "
            "(1: 全実行, 2: 正規化から, 3: 事業テーブル構築から, "
            "4: 予算サマリー構築から, 5: 資金の流れテーブル構築から, "
            "6: 支出テーブル構築から, 7: 既存ファイルのZIPアーカイブ作成のみ)"
        )
    )
    target_files: Optional[List[str]] = Field(
        default=None, 
        description="処理対象とするファイル名のリスト。指定しない場合はdownloadディレクトリ内の全ファイルが対象。"
    )

    # === ▼▼▼ 追加箇所 ▼▼▼ ===
    # Swagger UI (docs) に表示するリクエストボディのサンプルを定義
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "全ステージを実行 (推奨のデフォルト)",
                    "description": "全ファイルを対象に、パイプラインを最初から実行します。",
                    "value": {},
                },
                {
                    "summary": "ステージ3から再開",
                    "description": "正規化済みのデータを使って、マスターテーブル構築から処理を再開します。",
                    "value": {"start_stage": 3},
                },
                {
                    "summary": "特定ファイルのみを対象として実行",
                    "description": "指定したファイルのみを対象に、全ステージを実行します。",
                    "value": {
                        "target_files": ["database240918.zip", "database240502.zip"]
                    },
                },
            ]
        }
    )
    # ========================


class JobCreationResponse(BaseModel):
    """パイプライン実行開始APIのレスポンスモデル"""
    job_id: str
    message: str

class JobStatusResponse(BaseModel):
    """パイプラインステータス確認APIのレスポンスモデル"""
    job_id: str
    status: str  # "pending", "in-progress", "completed", "failed", "cancelled"
    current_stage: Optional[str] = None
    message: Optional[str] = None
    results_url: Optional[str] = None
    error_message: Optional[str] = None
    cancel_requested: bool = False