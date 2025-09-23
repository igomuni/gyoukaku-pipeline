document.addEventListener('DOMContentLoaded', () => {
    // DOM要素の取得
    const questionInput = document.getElementById('question');
    const loadSampleBtn = document.getElementById('load-sample-btn');
    const sqlInput = document.getElementById('sql-input');
    const executeSqlBtn = document.getElementById('execute-sql-btn');
    const resultMessage = document.getElementById('result-message');
    const resultTableContainer = document.getElementById('result-table-container');
    const copyCsvBtn = document.getElementById('copy-csv-btn');
    const downloadCsvBtn = document.getElementById('download-csv-btn');
    const historyList = document.getElementById('history-list');
    
    const refreshHistoryBtn = document.getElementById('refresh-history-btn');
    const exportHistoryBtn = document.getElementById('export-history-btn');
    const importHistoryBtn = document.getElementById('import-history-btn');
    const importHistoryInput = document.getElementById('import-history-input');
    const clearHistoryBtn = document.getElementById('clear-history-btn');

    const copyQuestionBtn = document.getElementById('copy-question-btn');
    const pasteQuestionBtn = document.getElementById('paste-question-btn');
    const copySqlBtn = document.getElementById('copy-sql-btn');
    const pasteSqlBtn = document.getElementById('paste-sql-btn');

    const showPromptModalBtn = document.getElementById('show-prompt-modal-btn');
    const promptModal = document.getElementById('prompt-modal');
    const promptModalTextarea = document.getElementById('prompt-modal-textarea');
    const copyPromptFromModalBtn = document.getElementById('copy-prompt-from-modal-btn');
    const closeModalBtn = document.querySelector('.close-btn');

    let promptTemplate = '';
    let currentResultData = null;
    let fullHistory = [];
    let dataTable = null;

    const sampleQuestions = [
        "省庁別の事業数が多い順にトップ5を教えて",
        "デジタル庁の事業のうち、当年度の当初予算額が高い順にトップ5の事業名と予算額を教えて",
        "各省庁の当年度の当初予算額の合計を計算し、合計額が多い順にトップ5の省庁名と合計額を教えて",
        "支出先テーブルで「一者応札」が理由となっている契約の、業務概要と支出先を教えて",
        "財務省が実施している事業で、3年前（_py3）の執行額が10億円（1000百万円）を超えている事業名を教えて",
    ];
    let sampleIndex = 0;

    const init = async () => {
        await fetchPromptTemplate();
        await fetchHistory();

        // ▼▼▼【ここからが修正点】▼▼▼
        // Initialize Split.js
        Split(['#col-1', '#col-2', '#col-3'], {
            sizes: [25, 45, 30], // Initial sizes in percentage
            minSize: [250, 450, 300], // Minimum size in pixels
            gutterSize: 10,
            cursor: 'col-resize',
            onDrag: () => {
                // Adjust DataTable column widths on resize
                if (dataTable) {
                    dataTable.columns.adjust().draw();
                }
            }
        });
        // ▲▲▲【ここまでが修正点】▲▲▲
    };

    const executeSql = async () => {
        const sql = sqlInput.value.trim();
        const question = questionInput.value.trim();
        if (!sql) { alert('SQLクエリを入力してください'); return; }
        resultMessage.textContent = '実行中...';
        if (dataTable) { dataTable.destroy(); dataTable = null; }
        resultTableContainer.innerHTML = '';
        executeSqlBtn.disabled = true;
        copyCsvBtn.style.display = 'none';
        downloadCsvBtn.style.display = 'none';
        currentResultData = null;
        try {
            const response = await fetch('/api/execute-sql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sql, question }),
            });
            const data = await response.json();
            if (response.ok) {
                currentResultData = data.result;
                renderResultTable(currentResultData);
                resultMessage.textContent = `成功 (${data.duration_ms}ms) - ${data.result.data.length}件`;
                if (data.result.data.length > 0) {
                    copyCsvBtn.style.display = 'inline-block';
                    downloadCsvBtn.style.display = 'inline-block';
                }
            } else {
                throw new Error(JSON.stringify(data.result.error || data.detail, null, 2));
            }
        } catch (error) {
            resultMessage.textContent = `エラーが発生しました`;
            resultTableContainer.innerHTML = `<pre style="color:red;">${error.message}</pre>`;
        } finally {
            executeSqlBtn.disabled = false;
            await fetchHistory();
        }
    };
    
    const renderResultTable = (data) => {
        if (dataTable) { dataTable.destroy(); dataTable = null; }
        resultTableContainer.innerHTML = '';
        if (!data || !data.columns || !data.data) {
            resultMessage.textContent = '結果が空または不正な形式です。';
            return;
        }
        const tableHeaders = data.columns.map(col => `<th>${escapeHtml(col)}</th>`).join('');
        const tableBody = data.data.map(rowData => {
            const cells = rowData.map(cellData => `<td>${escapeHtml(cellData === null ? '' : cellData)}</td>`).join('');
            return `<tr>${cells}</tr>`;
        }).join('');
        const tableHTML = `<table id="result-data-table" class="display" style="width:100%"><thead><tr>${tableHeaders}</tr></thead><tbody>${tableBody}</tbody></table>`;
        resultTableContainer.innerHTML = tableHTML;
        dataTable = new DataTable('#result-data-table', {
            scrollX: true,
            destroy: true,
            language: { "sProcessing": "処理中...", "sLengthMenu": "_MENU_ 件表示", "sZeroRecords": "データはありません。", "sInfo": "_TOTAL_ 件中 _START_ から _END_ まで表示", "sInfoEmpty": "0 件中 0 から 0 まで表示", "sInfoFiltered": "（全 _MAX_ 件より抽出）", "sInfoPostFix": "", "sSearch": "検索:", "sUrl": "", "oPaginate": { "sFirst": "先頭", "sPrevious": "前", "sNext": "次", "sLast": "最終" } }
        });
    };
    
    const fetchHistory = async () => {
        try {
            const response = await fetch('/api/history');
            if (!response.ok) throw new Error('履歴の取得に失敗しました');
            fullHistory = await response.json();
            renderHistory(fullHistory);
        } catch (error) {
            historyList.innerHTML = `<p style="color:red;">${error.message}</p>`;
        }
    };
    
    const exportHistory = () => {
        window.location.href = '/api/history/export';
    };

    const importHistory = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch('/api/history/import', { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'インポートに失敗しました');
            alert(result.message);
            await fetchHistory();
        } catch (error) {
            alert(`エラー: ${error.message}`);
        } finally {
            importHistoryInput.value = '';
        }
    };
    
    const clearHistory = async () => {
        if (!confirm('本当にすべての履歴を削除しますか？この操作は元に戻せません。')) return;
        try {
            const response = await fetch('/api/history/all', { method: 'DELETE' });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail);
            alert(result.message);
            await fetchHistory();
        } catch (error) {
            alert(`エラー: ${error.message}`);
        }
    };

    const deleteHistoryItem = async (historyId) => {
        if (!confirm(`ID:${historyId}の履歴を削除しますか？`)) return;
        try {
            const response = await fetch(`/api/history/${historyId}`, { method: 'DELETE' });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail);
            await fetchHistory();
        } catch (error) {
            alert(`エラー: ${error.message}`);
        }
    };
    
    const copyHistoryItem = (historyId) => {
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

    const renderHistory = (history) => {
        if (history.length === 0) {
            historyList.innerHTML = '<p>履歴はありません。</p>';
            return;
        }
        historyList.innerHTML = '';
        history.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            let resultInfo = "", resultDetails = "";
            const resultJson = JSON.parse(item.result_json || '{}');
            if (item.status === 'success') {
                const count = resultJson.data ? resultJson.data.length : 0;
                resultInfo = `<span class="history-result-info success">結果: ${count}件</span>`;
            } else if (item.status === 'error') {
                const errorMsg = resultJson.error || '不明なエラー';
                resultDetails = errorMsg;
                resultInfo = `<span class="history-result-info error" title="${escapeHtml(errorMsg)}">エラー</span>`;
            }
            div.innerHTML = `
                <div class="history-item-header">
                    <p>${escapeHtml(new Date(item.timestamp).toLocaleString())}</p>
                    <div class="history-item-actions">
                        <button class="copy-history-btn small-btn" data-history-id="${item.id}">コピー</button>
                        <button class="delete-history-btn icon-btn" data-history-id="${item.id}" title="削除">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                        </button>
                    </div>
                </div>
                <div class="history-item-body">
                    <p><span class="status ${item.status}">${item.status}</span> (${item.duration_ms}ms) ${resultInfo}</p>
                    <p><strong>質問:</strong> ${escapeHtml(item.question || 'N/A')}</p>
                    <div><strong>SQL:</strong><pre><code>${escapeHtml(item.sql_query)}</code></pre></div>
                    ${item.status === 'error' ? `<div><strong>エラー詳細:</strong><pre><code>${escapeHtml(resultDetails)}</code></pre></div>` : ''}
                </div>
            `;
            div.querySelector('.copy-history-btn').addEventListener('click', (e) => { e.stopPropagation(); copyHistoryItem(item.id); });
            div.querySelector('.delete-history-btn').addEventListener('click', (e) => { e.stopPropagation(); deleteHistoryItem(item.id); });
            div.addEventListener('click', (e) => { if(!e.target.closest('button')) { questionInput.value = item.question || ''; sqlInput.value = item.sql_query; } });
            historyList.appendChild(div);
        });
    };
    
    const getCsvContent = () => { if (!currentResultData) return null; const { columns, data } = currentResultData; const escapeCsvCell = (cell) => { const strCell = String(cell ?? ''); if (strCell.includes(',') || strCell.includes('"') || strCell.includes('\n')) { return `"${strCell.replace(/"/g, '""')}"`; } return strCell; }; const header = columns.map(escapeCsvCell).join(','); const rows = data.map(row => row.map(escapeCsvCell).join(',')); return [header, ...rows].join('\n'); };
    const copyResultAsCsv = () => { const csvContent = getCsvContent(); if (!csvContent) return; navigator.clipboard.writeText(csvContent).then(() => alert('結果をCSV形式でコピーしました！')).catch(err => alert('CSVのコピーに失敗しました: ' + err)); };
    const downloadResultAsCsv = () => { const csvContent = getCsvContent(); if (!csvContent) return; const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' }); const link = document.createElement("a"); const url = URL.createObjectURL(blob); link.setAttribute("href", url); const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, ""); link.setAttribute("download", `export_${timestamp}.csv`); link.style.visibility = 'hidden'; document.body.appendChild(link); link.click(); document.body.removeChild(link); };
    const fetchPromptTemplate = async () => { try { const response = await fetch('/api/get-prompt-template'); if (!response.ok) throw new Error('プロンプトの取得に失敗しました'); const data = await response.json(); promptTemplate = data.template; } catch (error) { alert(error.message); } };
    const getFormattedPrompt = () => { const question = questionInput.value.trim(); return promptTemplate.replace('{{question}}', question || '(ここに質問を入力)'); };
    const loadSampleQuestion = () => { questionInput.value = sampleQuestions[sampleIndex]; sampleIndex = (sampleIndex + 1) % sampleQuestions.length; };
    const openPromptModal = () => { promptModalTextarea.value = getFormattedPrompt(); promptModal.style.display = 'flex'; };
    const closePromptModal = () => { promptModal.style.display = 'none'; };
    const copyPromptFromModal = () => { navigator.clipboard.writeText(promptModalTextarea.value).then(() => alert('プロンプトをコピーしました！')).catch(err => alert('コピーに失敗しました: ' + err)); };
    const escapeHtml = (unsafe) => { return unsafe.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); };

    // --- イベントリスナーの設定 ---
    loadSampleBtn.addEventListener('click', loadSampleQuestion);
    executeSqlBtn.addEventListener('click', executeSql);
    copyCsvBtn.addEventListener('click', copyResultAsCsv);
    downloadCsvBtn.addEventListener('click', downloadResultAsCsv);
    refreshHistoryBtn.addEventListener('click', fetchHistory);
    exportHistoryBtn.addEventListener('click', exportHistory);
    importHistoryBtn.addEventListener('click', () => importHistoryInput.click());
    importHistoryInput.addEventListener('change', importHistory);
    clearHistoryBtn.addEventListener('click', clearHistory);
    
    copyQuestionBtn.addEventListener('click', () => navigator.clipboard.writeText(questionInput.value));
    pasteQuestionBtn.addEventListener('click', () => navigator.clipboard.readText().then(text => questionInput.value = text));
    copySqlBtn.addEventListener('click', () => navigator.clipboard.writeText(sqlInput.value));
    pasteSqlBtn.addEventListener('click', () => navigator.clipboard.readText().then(text => sqlInput.value = text));

    showPromptModalBtn.addEventListener('click', openPromptModal);
    closeModalBtn.addEventListener('click', closePromptModal);
    copyPromptFromModalBtn.addEventListener('click', copyPromptFromModal);
    window.addEventListener('click', (event) => { if (event.target == promptModal) closePromptModal(); });

    init();
});