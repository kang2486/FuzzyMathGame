"use strict";

/* ==================== 基本設定 ==================== */

const API_BASE = "";

const LEVEL_TYPE_IDS = {
    1: ["T001"],
    2: [],
    3: [],
    4: [],
    5: [],
    6: [],
    7: [],
    8: []
};

const INITIAL_SCORE = 50;
const PASS_SCORE = 80;
const QUESTION_TIME = 90;

let currentLevel = 1;
let currentTypeId = null;
let currentQuestion = null;
let currentScore = INITIAL_SCORE;
let remainingTime = QUESTION_TIME;
let timerId = null;
let selectedBlankId = null;
let gameFinished = false;


/* ==================== 頁面切換 ==================== */

function showPage(pageId) {
    const pageIds = [
        "home-page",
        "level-page",
        "game-page"
    ];

    pageIds.forEach((id) => {
        const element = document.getElementById(id);

        if (element) {
            element.style.display =
                id === pageId ? "block" : "none";
        }
    });
}

function showHomePage() {
    stopTimer();
    showPage("home-page");
}

function showLevelPage() {
    stopTimer();
    showPage("level-page");
}


/* ==================== 顯示回饋 ==================== */

function showFeedback(message, type = "info") {
    const element = document.getElementById("feedback");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `feedback ${type}`;
}


/* ==================== KaTeX 公式顯示 ==================== */

function renderLatex(expression, displayMode = false) {
    const text = String(expression ?? "");

    if (typeof window.katex === "undefined") {
        return escapeHtml(text);
    }

    try {
        return window.katex.renderToString(text, {
            throwOnError: false,
            displayMode,
            strict: "ignore"
        });
    } catch (error) {
        console.error("KaTeX 渲染失敗：", error);
        return escapeHtml(text);
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* ==================== 遊戲初始化 ==================== */

async function startGame(level) {
    stopTimer();

    currentLevel = Number(level);
    currentScore = INITIAL_SCORE;
    remainingTime = QUESTION_TIME;
    currentQuestion = null;
    selectedBlankId = null;
    gameFinished = false;

    updateScore();
    updateTimer();
    showPage("game-page");

    document.getElementById("question-box").textContent =
        "正在載入題目……";

    document.getElementById("process-box").textContent =
        "正在載入解題步驟……";

    showFeedback("");

    const typeIds = LEVEL_TYPE_IDS[currentLevel];

    if (!typeIds || typeIds.length === 0) {
        document.getElementById("question-box").textContent =
            "此章節目前尚未開放。";

        document.getElementById("process-box").textContent =
            "目前僅有第一章的 T001 題型可供測試。";

        showFeedback(
            "目前這個章節尚未設定題型資料。",
            "info"
        );

        return;
    }

    currentTypeId = typeIds[
        Math.floor(Math.random() * typeIds.length)
    ];

    try {
        const response = await fetch(
            `${API_BASE}/api/questions/generate-with-steps/${encodeURIComponent(currentTypeId)}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || `伺服器錯誤：${response.status}`
            );
        }

        currentQuestion = data;

        renderQuestion(data);
        renderProcess(data.steps || []);

        startTimer();

        showFeedback(
            "題目載入完成，請選取空格並填寫解題過程。",
            "info"
        );
    } catch (error) {
        console.error("載入題目失敗：", error);

        document.getElementById("question-box").textContent =
            "題目載入失敗。";

        document.getElementById("process-box").textContent =
            "請確認 Flask 後端已啟動、資料庫連線正常，並檢查終端機錯誤訊息。";

        showFeedback(error.message, "error");
    }
}


/* ==================== 題目顯示 ==================== */

function renderQuestion(data) {
    const questionBox = document.getElementById("question-box");

    const expression = data.latex_expression ?? "";

    questionBox.innerHTML =
        `<div class="math-expression">` +
        renderLatex(expression, true) +
        `</div>`;
}


/* ==================== 解題步驟顯示 ==================== */

function renderProcess(steps) {
    const processBox = document.getElementById("process-box");

    processBox.innerHTML = "";
    selectedBlankId = null;

    if (!Array.isArray(steps) || steps.length === 0) {
        processBox.textContent = "目前沒有可顯示的解題步驟。";
        return;
    }

    steps.forEach((step, index) => {
        const stepElement = document.createElement("div");
        stepElement.className = "process-step";

        const titleElement = document.createElement("div");
        titleElement.className = "step-title";
        titleElement.textContent =
            `步驟 ${step.order ?? index + 1}`;

        const contentElement = document.createElement("div");
        contentElement.className = "step-content";

        const content = String(step.content ?? "");

        /*
         * 空格標記格式：
         * [[blank:step_1]]
         *
         * 後端必須在 content 中提供標記，
         * 並在 blanks 中提供相同 ID 的標準答案。
         */
        const pattern = /\[\[blank:([a-zA-Z0-9_-]+)\]\]/g;

        let lastIndex = 0;
        let match;

        while ((match = pattern.exec(content)) !== null) {
            const precedingText = content.slice(
                lastIndex,
                match.index
            );

            appendLatex(contentElement, precedingText);

            const blankId = match[1];

            const button = document.createElement("button");
            button.type = "button";
            button.className = "input-slot";
            button.dataset.blankId = blankId;
            button.textContent = "填寫";

            button.addEventListener("click", () => {
                selectBlank(blankId);
            });

            contentElement.appendChild(button);

            lastIndex = pattern.lastIndex;
        }

        appendLatex(
            contentElement,
            content.slice(lastIndex)
        );

        stepElement.appendChild(titleElement);
        stepElement.appendChild(contentElement);
        processBox.appendChild(stepElement);
    });

    const slots = processBox.querySelectorAll(".input-slot");

    if (slots.length > 0) {
        selectBlank(slots[0].dataset.blankId);
    } else {
        showFeedback(
            "這份題目的解題步驟沒有設定填答空格，請確認後端步驟資料。",
            "error"
        );
    }
}

function appendLatex(parent, text) {
    if (!text) {
        return;
    }

    const wrapper = document.createElement("span");
    wrapper.className = "math-expression";
    wrapper.innerHTML = renderLatex(text);

    parent.appendChild(wrapper);
}


/* ==================== 選取填答空格 ==================== */

function selectBlank(blankId) {
    if (gameFinished) {
        return;
    }

    selectedBlankId = blankId;

    document.querySelectorAll(".input-slot").forEach((slot) => {
        slot.classList.toggle(
            "selected",
            slot.dataset.blankId === blankId
        );
    });

    showFeedback(
        `目前選取空格：${blankId}。請使用下方鍵盤輸入答案。`,
        "info"
    );
}


/* ==================== 鍵盤輸入 ==================== */

function insertMath(value) {
    if (gameFinished) {
        return;
    }

    if (!selectedBlankId) {
        showFeedback("請先點選一個解題空格。", "error");
        return;
    }

    const slot = findSelectedSlot();

    if (!slot) {
        showFeedback("找不到目前選取的空格，請重新選取。", "error");
        return;
    }

    const currentValue =
        slot.dataset.answerValue || "";

    const newValue = currentValue + String(value);

    setSlotValue(slot, newValue);
}

function backspaceMath() {
    if (gameFinished) {
        return;
    }

    const slot = findSelectedSlot();

    if (!slot) {
        showFeedback("請先選取要修改的空格。", "error");
        return;
    }

    const currentValue =
        slot.dataset.answerValue || "";

    setSlotValue(slot, currentValue.slice(0, -1));
}

function clearSelectedBlank() {
    const slot = findSelectedSlot();

    if (!slot) {
        return;
    }

    setSlotValue(slot, "");
}

function findSelectedSlot() {
    if (!selectedBlankId) {
        return null;
    }

    return document.querySelector(
        `.input-slot[data-blank-id="${CSS.escape(selectedBlankId)}"]`
    );
}

function setSlotValue(slot, value) {
    slot.dataset.answerValue = value;
    slot.textContent = value || "填寫";
    slot.classList.toggle("filled", value.length > 0);
}


/* ==================== 整理答案 ==================== */

function collectAnswers() {
    const slots = document.querySelectorAll(".input-slot");

    return Array.from(slots).map((slot) => ({
        blank_id: slot.dataset.blankId,
        value: slot.dataset.answerValue || ""
    }));
}


/* ==================== 提交答案 ==================== */

async function checkAnswer() {
    if (gameFinished) {
        return;
    }

    if (!currentQuestion || !currentTypeId) {
        showFeedback("目前沒有可提交的題目。", "error");
        return;
    }

    const answers = collectAnswers();

    if (answers.length === 0) {
        showFeedback(
            "這份題目沒有填答空格，請先確認後端解題步驟。",
            "error"
        );
        return;
    }

    const emptyAnswers = answers.filter(
        (answer) => !answer.value.trim()
    );

    if (emptyAnswers.length > 0) {
        showFeedback(
            `還有 ${emptyAnswers.length} 個空格尚未填寫。`,
            "error"
        );
        return;
    }

    const submitButton = document.querySelector(
        '.answer-actions button[onclick="checkAnswer()"]'
    );

    if (submitButton) {
        submitButton.disabled = true;
    }

    try {
        const response = await fetch(`${API_BASE}/api/check-answer`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                type_id: currentTypeId,
                difficulty: currentQuestion.difficulty ?? 1,
                answers
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || `答案檢查失敗：${response.status}`
            );
        }

        if (typeof data.score === "number") {
            currentScore = data.score;
        } else if (typeof data.score_change === "number") {
            currentScore = Math.max(
                0,
                Math.min(100, currentScore + data.score_change)
            );
        }

        updateScore();

        if (Array.isArray(data.results)) {
            data.results.forEach((result) => {
                const slot = document.querySelector(
                    `.input-slot[data-blank-id="${CSS.escape(result.blank_id)}"]`
                );

                if (!slot) {
                    return;
                }

                slot.classList.remove("correct", "incorrect");

                slot.classList.add(
                    result.correct ? "correct" : "incorrect"
                );
            });
        }

        if (data.correct) {
            showFeedback(
                data.message || "回答正確！",
                "success"
            );
        } else {
            showFeedback(
                data.message || "部分答案不正確，請檢查解題步驟。",
                "error"
            );
        }

        if (currentScore >= PASS_SCORE) {
            finishGame(
                "恭喜！目前分數已達到通過門檻。"
            );
        } else if (data.finished === true) {
            finishGame(
                data.message || "本次挑戰已結束。"
            );
        }
    } catch (error) {
        console.error("提交答案失敗：", error);

        showFeedback(
            `${error.message}。請確認後端已實作 /api/check-answer。`,
            "error"
        );
    } finally {
        if (submitButton && !gameFinished) {
            submitButton.disabled = false;
        }
    }
}


/* ==================== 分數顯示 ==================== */

function updateScore() {
    const scoreElement = document.getElementById("score");

    if (scoreElement) {
        scoreElement.textContent = String(currentScore);
    }
}


/* ==================== 計時器 ==================== */

function startTimer() {
    stopTimer();

    remainingTime = QUESTION_TIME;
    updateTimer();

    timerId = window.setInterval(() => {
        if (gameFinished) {
            stopTimer();
            return;
        }

        remainingTime -= 1;
        updateTimer();

        if (remainingTime <= 0) {
            finishGame("時間到！本次挑戰已結束。");
        }
    }, 1000);
}

function stopTimer() {
    if (timerId !== null) {
        window.clearInterval(timerId);
        timerId = null;
    }
}

function updateTimer() {
    const timerElement = document.getElementById("timer");

    if (timerElement) {
        timerElement.textContent = String(
            Math.max(0, remainingTime)
        );
    }
}


/* ==================== 結束遊戲 ==================== */

function finishGame(message) {
    gameFinished = true;
    stopTimer();

    document.querySelectorAll(".input-slot").forEach((slot) => {
        slot.disabled = true;
    });

    const submitButton = document.querySelector(
        '.answer-actions button[onclick="checkAnswer()"]'
    );

    if (submitButton) {
        submitButton.disabled = true;
    }

    showFeedback(
        `${message} 目前分數：${currentScore} 分。`,
        currentScore >= PASS_SCORE ? "success" : "info"
    );
}


/* ==================== 頁面載入完成 ==================== */

document.addEventListener("DOMContentLoaded", () => {
    showPage("home-page");
    updateScore();
    updateTimer();
});
