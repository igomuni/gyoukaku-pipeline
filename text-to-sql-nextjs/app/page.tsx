'use client';

import { useEffect, useRef, useState } from 'react';
import Split from 'split.js';
import $ from 'jquery';
import DataTable from 'datatables.net-dt';
import 'datatables.net-dt/css/dataTables.dataTables.css';

// DataTablesにjQueryを設定
if (typeof window !== 'undefined') {
  (window as any).jQuery = $;
  (window as any).$ = $;
}

interface HistoryItem {
  id: number;
  timestamp: string;
  question: string | null;
  sql_query: string;
  status: string;
  result_json: string;
  duration_ms: number;
  execution_count: number;
}

interface ResultData {
  columns: string[];
  data: any[][];
}

export default function Home() {
  const [question, setQuestion] = useState('');
  const [sql, setSql] = useState('');
  const [resultMessage, setResultMessage] = useState('まだ実行されていません');
  const [currentResultData, setCurrentResultData] = useState<ResultData | null>(null);
  const [fullHistory, setFullHistory] = useState<HistoryItem[]>([]);
  const [promptTemplate, setPromptTemplate] = useState('');
  const [showPromptModal, setShowPromptModal] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [lastLoadedHistoryItem, setLastLoadedHistoryItem] = useState<any>(null);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  const dataTableRef = useRef<any>(null);
  const resultTableContainerRef = useRef<HTMLDivElement>(null);

  const sampleQuestions = [
    "省庁別の事業数が多い順にトップ5を教えて",
    "デジタル庁の事業のうち、当年度の当初予算額が高い順にトップ5の事業名と予算額を教えて",
    "各省庁の当年度の当初予算額の合計を計算し、合計額が多い順にトップ5の省庁名と合計額を教えて",
    "支出先テーブルで「一者応札」が理由となっている契約の、業務概要と支出先を教えて",
    "財務省が実施している事業で、3年前(_py3)の執行額が10億円(1000百万円)を超えている事業名を教えて",
  ];
  const [sampleIndex, setSampleIndex] = useState(0);

  useEffect(() => {
    const initSplit = Split(['#col-1', '#col-2', '#col-3'], {
      sizes: [25, 45, 30],
      minSize: [250, 450, 300],
      gutterSize: 10,
      cursor: 'col-resize',
      onDrag: () => {
        if (dataTableRef.current) {
          dataTableRef.current.columns.adjust().draw();
        }
      }
    });

    fetchPromptTemplate();
    fetchHistory();

    return () => {
      if (initSplit) {
        initSplit.destroy();
      }
    };
  }, []);

  const fetchPromptTemplate = async () => {
    try {
      const response = await fetch('/api/get-prompt-template');
      if (!response.ok) throw new Error('プロンプトの取得に失敗しました');
      const data = await response.json();
      setPromptTemplate(data.template);
    } catch (error: any) {
      alert(error.message);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/history');
      if (!response.ok) throw new Error('履歴の取得に失敗しました');
      const data = await response.json();
      setFullHistory(data);

      if (isInitialLoad && data.length > 0) {
        loadHistoryItemIntoForm(data[0]);
        setIsInitialLoad(false);
      }
    } catch (error: any) {
      console.error('履歴の取得エラー:', error.message);
    }
  };

  const loadHistoryItemIntoForm = (item: HistoryItem) => {
    setQuestion(item.question || '');
    setSql(item.sql_query || '');
    setLastLoadedHistoryItem({
      id: item.id,
      question: item.question,
      sql_query: item.sql_query
    });
  };

  const executeSql = async () => {
    const currentQuestion = question.trim();
    const currentSql = sql.trim();
    if (!currentSql) {
      alert('SQLクエリを入力してください');
      return;
    }

    setResultMessage('実行中...');
    setIsExecuting(true);
    if (dataTableRef.current) {
      dataTableRef.current.destroy();
      dataTableRef.current = null;
    }
    if (resultTableContainerRef.current) {
      resultTableContainerRef.current.innerHTML = '';
    }
    setCurrentResultData(null);

    try {
      let historyIdToSend = null;
      if (lastLoadedHistoryItem &&
          (lastLoadedHistoryItem.question || '').trim() === currentQuestion &&
          (lastLoadedHistoryItem.sql_query || '').trim() === currentSql) {
        historyIdToSend = lastLoadedHistoryItem.id;
      }

      const payload = {
        sql: currentSql,
        question: currentQuestion,
        history_id: historyIdToSend
      };

      const response = await fetch('/api/execute-sql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (response.ok) {
        setCurrentResultData(data.result);
        renderResultTable(data.result);
        setResultMessage(`成功 (${data.duration_ms}ms) - ${data.result.data.length}件`);
      } else {
        throw new Error(JSON.stringify(data.result?.error || data.detail, null, 2));
      }
    } catch (error: any) {
      setResultMessage('エラーが発生しました');
      if (resultTableContainerRef.current) {
        resultTableContainerRef.current.innerHTML = `<pre style="color:red;">${error.message}</pre>`;
      }
    } finally {
      setIsExecuting(false);
      setLastLoadedHistoryItem(null);
      await fetchHistory();
    }
  };

  const renderResultTable = (data: ResultData) => {
    if (dataTableRef.current) {
      dataTableRef.current.destroy();
      dataTableRef.current = null;
    }
    if (!resultTableContainerRef.current) return;
    resultTableContainerRef.current.innerHTML = '';

    if (!data || !data.columns || !data.data) {
      setResultMessage('結果が空または不正な形式です。');
      return;
    }

    const tableHeaders = data.columns.map(col => `<th>${escapeHtml(col)}</th>`).join('');
    const tableBody = data.data.map(rowData => {
      const cells = rowData.map(cellData => `<td>${escapeHtml(cellData === null ? '' : cellData)}</td>`).join('');
      return `<tr>${cells}</tr>`;
    }).join('');
    const tableHTML = `<table id="result-data-table" class="display" style="width:100%"><thead><tr>${tableHeaders}</tr></thead><tbody>${tableBody}</tbody></table>`;
    resultTableContainerRef.current.innerHTML = tableHTML;

    dataTableRef.current = new DataTable('#result-data-table', {
      scrollX: true,
      destroy: true,
      language: {
        processing: "処理中...",
        lengthMenu: "_MENU_ 件表示",
        zeroRecords: "データはありません。",
        info: "_TOTAL_ 件中 _START_ から _END_ まで表示",
        infoEmpty: "0 件中 0 から 0 まで表示",
        infoFiltered: "(全 _MAX_ 件より抽出)",
        infoPostFix: "",
        search: "検索:",
        url: "",
        paginate: {
          first: "先頭",
          previous: "前",
          next: "次",
          last: "最終"
        }
      }
    });
  };

  const loadSampleQuestion = () => {
    setQuestion(sampleQuestions[sampleIndex]);
    setSql('');
    setSampleIndex((sampleIndex + 1) % sampleQuestions.length);
    setLastLoadedHistoryItem(null);
  };

  const getCsvContent = () => {
    if (!currentResultData) return null;
    const { columns, data } = currentResultData;
    const escapeCsvCell = (cell: any) => {
      const strCell = String(cell ?? '');
      if (strCell.includes(',') || strCell.includes('"') || strCell.includes('\n')) {
        return `"${strCell.replace(/"/g, '""')}"`;
      }
      return strCell;
    };
    const header = columns.map(escapeCsvCell).join(',');
    const rows = data.map(row => row.map(escapeCsvCell).join(','));
    return [header, ...rows].join('\n');
  };

  const copyResultAsCsv = () => {
    const csvContent = getCsvContent();
    if (!csvContent) return;
    navigator.clipboard.writeText(csvContent).then(() => alert('結果をCSV形式でコピーしました!')).catch(err => alert('CSVのコピーに失敗しました: ' + err));
  };

  const downloadResultAsCsv = () => {
    const csvContent = getCsvContent();
    if (!csvContent) return;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, "");
    link.setAttribute("download", `export_${timestamp}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportHistory = () => {
    window.location.href = '/api/history/export';
  };

  const importHistory = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch('/api/history/import', { method: 'POST', body: formData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'インポートに失敗しました');
      alert(result.message);
      await fetchHistory();
    } catch (error: any) {
      alert(`エラー: ${error.message}`);
    } finally {
      event.target.value = '';
    }
  };

  const clearHistory = async () => {
    if (!confirm('本当にすべての履歴を削除しますか?この操作は元に戻せません。')) return;
    try {
      const response = await fetch('/api/history/all', { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail);
      alert(result.message);
      await fetchHistory();
    } catch (error: any) {
      alert(`エラー: ${error.message}`);
    }
  };

  const deleteHistoryItem = async (historyId: number) => {
    if (!confirm(`ID:${historyId}の履歴を削除しますか?`)) return;
    try {
      const response = await fetch(`/api/history/${historyId}`, { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail);
      await fetchHistory();
    } catch (error: any) {
      alert(`エラー: ${error.message}`);
    }
  };

  const copyHistoryItem = (historyId: number) => {
    const item = fullHistory.find(h => h.id === historyId);
    if (!item) return;
    let resultInfo = "";
    const resultJson = JSON.parse(item.result_json || '{}');
    if (item.status === 'success') {
      resultInfo = `結果: ${resultJson.data ? resultJson.data.length : 0}件`;
    } else {
      resultInfo = `エラー: ${resultJson.error || 'N/A'}`;
    }
    const textToCopy = `--- 実行履歴 ---\n日時: ${new Date(item.timestamp).toLocaleString()}\nステータス: ${item.status} (${item.duration_ms}ms)\n${resultInfo}\n-----------------\n質問:\n${item.question || 'N/A'}\n-----------------\nSQL:\n${item.sql_query}\n-----------------`;
    navigator.clipboard.writeText(textToCopy.trim()).then(() => alert('履歴をコピーしました')).catch(err => alert('コピーに失敗しました: ' + err));
  };

  const getFormattedPrompt = () => {
    return promptTemplate.replace('{{question}}', question.trim() || '(ここに質問を入力)');
  };

  const copyPromptFromModal = () => {
    const formattedPrompt = getFormattedPrompt();
    navigator.clipboard.writeText(formattedPrompt).then(() => alert('プロンプトをコピーしました!')).catch(err => alert('コピーに失敗しました: ' + err));
  };

  const escapeHtml = (unsafe: any) => {
    return unsafe.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  };

  return (
    <div className="container">
      <header className="app-header">
        <h1>Text-to-SQL 実験ツール</h1>
        <button onClick={() => setShowPromptModal(true)} className="btn-primary">外部LLMでSQL生成する</button>
      </header>

      <div className="three-column-grid" id="main-grid">
        <div className="column" id="col-1">
          <div className="card">
            <h2>1. 質問の入力</h2>
            <label htmlFor="question">自然言語で質問を入力</label>
            <div className="textarea-wrapper">
              <textarea
                id="question"
                rows={4}
                placeholder="例: 省庁別の事業数トップ5を教えて"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
              <div className="textarea-icons">
                <button onClick={() => navigator.clipboard.writeText(question)} className="icon-btn" title="コピー">📋</button>
                <button onClick={() => navigator.clipboard.readText().then(text => setQuestion(text))} className="icon-btn" title="貼り付け">📄</button>
              </div>
            </div>
            <div className="action-buttons">
              <button onClick={loadSampleQuestion} className="btn-secondary">サンプル質問</button>
            </div>
          </div>
          <div className="card">
            <h2>2. SQLの実行</h2>
            <label htmlFor="sql-input">LLMが生成したSQLクエリ</label>
            <div className="textarea-wrapper">
              <textarea
                id="sql-input"
                rows={12}
                placeholder="ここにSQLを貼り付けて実行します"
                value={sql}
                onChange={(e) => setSql(e.target.value)}
              />
              <div className="textarea-icons">
                <button onClick={() => navigator.clipboard.writeText(sql)} className="icon-btn" title="コピー">📋</button>
                <button onClick={() => navigator.clipboard.readText().then(text => setSql(text))} className="icon-btn" title="貼り付け">📄</button>
              </div>
            </div>
            <button onClick={executeSql} disabled={isExecuting} className="btn-primary">SQLを実行</button>
          </div>
        </div>

        <div className="column" id="col-2">
          <div className="card result-card">
            <h2>3. 実行結果</h2>
            <div className="result-header">
              <span className="result-message">{resultMessage}</span>
              <div className="result-actions">
                {currentResultData && currentResultData.data.length > 0 && (
                  <>
                    <button onClick={copyResultAsCsv} className="small-btn">CSVコピー</button>
                    <button onClick={downloadResultAsCsv} className="small-btn">CSVダウンロード</button>
                  </>
                )}
              </div>
            </div>
            <div ref={resultTableContainerRef} className="result-table-container"></div>
          </div>
        </div>

        <div className="column" id="col-3">
          <div className="card history-card">
            <h2>実行履歴</h2>
            <div className="history-header">
              <button onClick={fetchHistory} className="small-btn">更新</button>
              <button onClick={exportHistory} className="small-btn">エクスポート</button>
              <button onClick={() => document.getElementById('import-history-input')?.click()} className="small-btn">インポート</button>
              <button onClick={clearHistory} className="small-btn danger">全件クリア</button>
              <input type="file" id="import-history-input" accept=".json" style={{ display: 'none' }} onChange={importHistory} />
            </div>
            <div className="history-list">
              {fullHistory.length === 0 ? (
                <p>履歴はありません。</p>
              ) : (
                fullHistory.map(item => {
                  const resultJson = JSON.parse(item.result_json || '{}');
                  let resultInfo = "";
                  let resultDetails = "";
                  if (item.status === 'success') {
                    const count = resultJson.data ? resultJson.data.length : 0;
                    resultInfo = `結果: ${count}件`;
                  } else if (item.status === 'error') {
                    const errorMsg = resultJson.error || '不明なエラー';
                    resultDetails = errorMsg;
                    resultInfo = `エラー`;
                  }
                  return (
                    <div key={item.id} className="history-item" onClick={(e) => {
                      if (!(e.target as HTMLElement).closest('button')) {
                        loadHistoryItemIntoForm(item);
                      }
                    }}>
                      <div className="history-item-header">
                        <p>
                          <span className="execution-count" title="実行回数">{item.execution_count || 1}</span>
                          {new Date(item.timestamp).toLocaleString()}
                        </p>
                        <div className="history-item-actions">
                          <button onClick={(e) => { e.stopPropagation(); copyHistoryItem(item.id); }} className="small-btn">コピー</button>
                          <button onClick={(e) => { e.stopPropagation(); deleteHistoryItem(item.id); }} className="icon-btn" title="削除">🗑️</button>
                        </div>
                      </div>
                      <div className="history-item-body">
                        <p><span className={`status ${item.status}`}>{item.status}</span> ({item.duration_ms}ms) {resultInfo}</p>
                        <p><strong>質問:</strong> {item.question || 'N/A'}</p>
                        <div><strong>SQL:</strong><pre><code>{item.sql_query}</code></pre></div>
                        {item.status === 'error' && <div><strong>エラー詳細:</strong><pre><code>{resultDetails}</code></pre></div>}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>

      {showPromptModal && (
        <div className="modal-overlay" onClick={() => setShowPromptModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>外部LLMでSQLを生成する</h2>
            </div>
            <p className="modal-instructions">
              以下のプロンプト全体をコピーし、ChatGPTやGeminiなどの外部LLMに貼り付けてSQLを生成してください。<br />
              必要に応じて、プロンプトの内容(特に指示部分)を直接編集することも可能です。
            </p>
            <div className="textarea-wrapper">
              <textarea rows={18} value={getFormattedPrompt()} readOnly />
              <div className="textarea-icons">
                <button onClick={copyPromptFromModal} className="icon-btn" title="コピー">📋</button>
              </div>
            </div>
            <span className="close-btn" onClick={() => setShowPromptModal(false)}>&times;</span>
          </div>
        </div>
      )}
    </div>
  );
}