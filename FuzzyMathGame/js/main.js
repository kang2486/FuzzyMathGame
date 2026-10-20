
"use strict";

/* =====================================================
   FuzzyMathGame - 四道門路徑選擇版
   1. 保留 Flask 題目 API
   2. 保留 Fuzzy 能力值 API
   3. 四選一，逐步完成標準解題步驟
   4. 每次選錯扣 HP 和 Fuzzy 能力值
   5. HP 歸零後重生並換題
   6. 完成全部步驟才算整題答對
   7. 保留 MP、提示、計時及通關條件
===================================================== */


/* ==================== 1. 遊戲設定 ==================== */

const API_BASE = "";

const INITIAL_HP = 100;
const INITIAL_MP = 100;
const INITIAL_ABILITY = 50;

const MAX_ABILITY = 100;
const PASS_ABILITY = 80;

const DEFAULT_DIFFICULTY = 3;

const QUESTION_TIME_BY_DIFFICULTY = {
    1: 60,
    2: 90,
    3: 120,
    4: 150,
    5: 180
};

const HP_LOSS = 25;
const MP_RECOVERY = 10;
const HINT_MP_COST = 20;
const MAX_HINT_COUNT = 5;

const LEVEL_TYPE_IDS = {
    1: Array.from(
        { length: 20 },
        (_, index) => `F${String(index + 1).padStart(2, "0")}`
    ),
    2: [],
    3: [],
    4: [],
    5: [],
    6: [],
    7: [],
    8: []
};

const LEVEL_NAMES = {
    1: "函數與數學基礎",
    2: "極限與連續",
    3: "微分的基本概念",
    4: "微分法則",
    5: "微分的應用",
    6: "不定積分",
    7: "定積分",
    8: "積分的應用"
};


let bankLabel = "";
async function refreshBankConfig() {
    const response = await fetch(`${API_BASE}/api/game-config`, {cache: "no-store"});
    const config = await response.json();
    if (!response.ok) throw new Error(config.message || "無法讀取題庫設定");
    for (let chapter = 1; chapter <= 8; chapter++) {
        LEVEL_TYPE_IDS[chapter] = config.chapters?.[String(chapter)] || [];
    }
    bankLabel = config.label;
    document.querySelectorAll("#level-list .level-card").forEach((button, index) => {
        const available = LEVEL_TYPE_IDS[index + 1].length > 0;
        button.disabled = !available;
        button.title = available ? "開啟本章題目" : "本章題庫尚未建立";
        button.style.opacity = available ? "1" : "0.45";
    });
}

/* ==================== 2. 遊戲狀態 ==================== */

let currentLevel = 1;
let currentTypeId = null;
let currentQuestion = null;

let currentHP = INITIAL_HP;
let currentMP = INITIAL_MP;
let currentAbility = INITIAL_ABILITY;

let remainingTime = QUESTION_TIME_BY_DIFFICULTY[DEFAULT_DIFFICULTY];
let currentQuestionTime = remainingTime;

let currentHintCount = 0;
let currentStepIndex = 0;
let currentSteps = [];
let currentChoices = [];

let timerId = null;
let nextQuestionTimeoutId = null;

let loadingQuestion = false;
let gameFinished = false;
let answerLocked = false;
let abilityRequestInProgress = false;

let questionRequestId = 0;
let gameSessionId = 0;
let lastQuestionTypeId = null;


/* ==================== 3. DOM 與頁面切換 ==================== */

function getElement(id) {
    return document.getElementById(id);
}

function showPage(pageId) {
    document.querySelectorAll(".app-shell > .page").forEach(page => {
        page.classList.toggle("hidden", page.id !== pageId);
    });
}

function showHomePage() {
    leaveGame();
    showPage("home-page");
}

async function showLevelPage() {
    leaveGame();
    showPage("level-page");
    try {
        await refreshBankConfig();
    } catch (error) {
        alert(`題庫讀取失敗：${error.message}`);
    }
}

function leaveGame() {
    questionRequestId++;
    gameSessionId++;

    stopTimer();
    clearNextQuestionTimeout();

    loadingQuestion = false;
    gameFinished = false;
    answerLocked = false;
    abilityRequestInProgress = false;

    currentQuestion = null;
    currentSteps = [];
    currentChoices = [];
}

function clearNextQuestionTimeout() {
    if (nextQuestionTimeoutId !== null) {
        window.clearTimeout(nextQuestionTimeoutId);
        nextQuestionTimeoutId = null;
    }
}


/* ==================== 4. 回饋訊息 ==================== */

function showFeedback(message, type = "info") {
    const element = getElement("feedback-message");
    if (!element) return;

    element.textContent = message;
    element.dataset.type = type;

    element.classList.remove("success", "error");

    if (type === "success") {
        element.classList.add("success");
    } else if (type === "error") {
        element.classList.add("error");
    }
}

function clearFeedback() {
    showFeedback("");
}


/* ==================== 5. 更新狀態 ==================== */

function updateStatus() {
    const values = [
        ["hp-value", currentHP],
        ["mp-value", currentMP],
        ["ability-value", currentAbility],
        ["timer", remainingTime]
    ];

    values.forEach(([id, value]) => {
        const element = getElement(id);
        if (element) element.textContent = value;
    });

    const bars = [
        ["hp-bar", currentHP / INITIAL_HP * 100],
        ["mp-bar", currentMP / INITIAL_MP * 100],
        ["ability-bar", currentAbility / MAX_ABILITY * 100]
    ];

    bars.forEach(([id, percent]) => {
        const element = getElement(id);
        if (element) {
            element.style.width =
                `${Math.max(0, Math.min(100, percent))}%`;
        }
    });

    updateQuestionDifficultyLabel();
}

function updateQuestionDifficultyLabel() {
    const element = getElement("question-difficulty");
    if (!element || !currentQuestion) return;

    element.textContent =
        `難度：${currentQuestion.difficulty ?? "未知"}｜能力值：${currentAbility}`;
}


/* ==================== 6. KaTeX 數學公式 ==================== */

function normalizeMathSigns(value) {
    return String(value ?? "")
        .replace(/−/g, "-")
        .trim();
}

function normalizeLatex(value) {
    let text = normalizeMathSigns(value);
    if (!text) return "";

    if (
        text.startsWith("\\(") ||
        text.startsWith("\\[") ||
        text.startsWith("$")
    ) {
        return text;
    }

    return `\\(${text}\\)`;
}

function appendMath(parent, value) {
    const element = document.createElement("span");
    element.className = "math-content";
    element.textContent = normalizeLatex(value);
    parent.appendChild(element);
    return element;
}

function renderMath(element) {
    if (
        !element ||
        typeof window.renderMathInElement !== "function"
    ) {
        return;
    }

    window.renderMathInElement(element, {
        delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\[", right: "\\]", display: true },
            { left: "\\(", right: "\\)", display: false },
            { left: "$", right: "$", display: false }
        ],
        throwOnError: false,
        strict: "ignore"
    });
}


/* ==================== 7. 題目時間 ==================== */

function getQuestionTime(difficulty) {
    return QUESTION_TIME_BY_DIFFICULTY[Number(difficulty)]
        || QUESTION_TIME_BY_DIFFICULTY[DEFAULT_DIFFICULTY];
}

function getElapsedTime() {
    return Math.max(
        0,
        Math.min(
            currentQuestionTime,
            currentQuestionTime - remainingTime
        )
    );
}


/* ==================== 8. 開始遊戲 ==================== */

async function startGame(level) {
    const selectedLevel = Number(level);
    try {
        await refreshBankConfig();
    } catch (error) {
        alert(`題庫讀取失敗：${error.message}`);
        return;
    }
    const availableTypes = LEVEL_TYPE_IDS[selectedLevel] || [];

    if (availableTypes.length === 0) {
        alert("這個章節目前尚未開放題目。");
        return;
    }

    leaveGame();

    currentLevel = selectedLevel;
    currentTypeId = null;
    lastQuestionTypeId = null;

    currentHP = INITIAL_HP;
    currentMP = INITIAL_MP;
    currentAbility = INITIAL_ABILITY;

    currentQuestionTime =
        QUESTION_TIME_BY_DIFFICULTY[DEFAULT_DIFFICULTY];
    remainingTime = currentQuestionTime;

    currentHintCount = 0;
    currentStepIndex = 0;
    currentSteps = [];
    currentChoices = [];

    gameFinished = false;
    loadingQuestion = false;
    answerLocked = false;
    abilityRequestInProgress = false;

    const chapterLabel = getElement("chapter-label");
    if (chapterLabel) {
        chapterLabel.textContent =
            `CHAPTER ${String(currentLevel).padStart(2, "0")}`;
    }

    const questionBox = getElement("question-box");
    if (questionBox) {
        questionBox.textContent = "正在載入題目……";
    }

    showPage("game-page");
    updateStatus();

    await loadNextQuestion();
}


/* ==================== 9. 載入題目 ==================== */

async function loadNextQuestion() {
    if (
        loadingQuestion ||
        gameFinished ||
        abilityRequestInProgress
    ) {
        return;
    }

    const chapterLabel = getElement("chapter-label");
    if (chapterLabel) chapterLabel.textContent = `CHAPTER ${String(currentLevel).padStart(2, "0")} · ${bankLabel}`;
    const availableTypes = LEVEL_TYPE_IDS[currentLevel] || [];

    if (availableTypes.length === 0) {
        showFeedback("目前章節沒有可用的題型。", "error");
        return;
    }

    const candidates = availableTypes.filter(
        id => id !== lastQuestionTypeId
    );

    const pool = candidates.length > 0 ? candidates : availableTypes;

    currentTypeId = pool[Math.floor(Math.random() * pool.length)];
    lastQuestionTypeId = currentTypeId;

    loadingQuestion = true;
    answerLocked = true;

    stopTimer();
    clearNextQuestionTimeout();

    const requestId = ++questionRequestId;

    const questionBox = getElement("question-box");
    if (questionBox) {
        questionBox.textContent = "正在載入題目……";
    }

    resetDoorArea();

    try {
        const url =
            `${API_BASE}/api/questions/generate-with-steps/` +
            `${encodeURIComponent(currentTypeId)}` +
            `?ability=${encodeURIComponent(currentAbility)}`;

        const response = await fetch(url);
        const rawText = await response.text();

        let data;

        try {
            data = JSON.parse(rawText);
        } catch {
            throw new Error(
                `後端沒有回傳有效 JSON：${rawText.slice(0, 150)}`
            );
        }

        if (!response.ok) {
            throw new Error(
                data.message || data.error || `HTTP ${response.status}`
            );
        }

        if (data.status && data.status !== "success") {
            throw new Error(
                data.message || data.error || "後端未成功產生題目。"
            );
        }

        if (requestId !== questionRequestId) return;

        const difficulty = Number(data.difficulty);

        data.difficulty =
            Number.isInteger(difficulty) &&
            difficulty >= 1 &&
            difficulty <= 5
                ? difficulty
                : DEFAULT_DIFFICULTY;

        currentQuestion = data;

        currentSteps =
            data.steps ||
            data["步驟"] ||
            [];

        if (!Array.isArray(currentSteps) || currentSteps.length === 0) {
            throw new Error("題目沒有提供標準解題步驟，無法進行路徑選擇。");
        }

        currentStepIndex = 0;
        currentHintCount = 0;

        currentQuestionTime = getQuestionTime(data.difficulty);
        remainingTime = currentQuestionTime;

        renderQuestion(data);
        renderCurrentStep();

        updateStatus();
        clearFeedback();
        answerLocked = false;
        startTimer();

        console.log("題目資料：", data);
        console.log("標準步驟：", currentSteps);
    } catch (error) {
        console.error("載入題目失敗：", error);

        if (requestId === questionRequestId) {
            if (questionBox) {
                questionBox.textContent = "題目載入失敗。";
            }

            showFeedback(
                `載入題目失敗：${error.message}`,
                "error"
            );
        }
    } finally {
        if (requestId === questionRequestId) {
            loadingQuestion = false;
            answerLocked = false;
        }
    }
}


/* ==================== 10. 顯示題目 ==================== */

function renderQuestion(data) {
    const box = getElement("question-box");
    if (!box) return;

    box.replaceChildren();

    const questionText = String(
        data.question_text || data.question || ""
    ).trim();

    const questionLatex = String(
        data.question_latex ||
        data.latex_expression ||
        data.expression ||
        ""
    ).trim();

    if (questionText) {
        const description = document.createElement("div");
        description.className = "question-description";
        description.textContent = questionText;
        box.appendChild(description);
    }

    if (questionLatex) {
        const formula = document.createElement("div");
        formula.className = "question-expression";
        appendMath(formula, questionLatex);
        box.appendChild(formula);
    }

    if (!questionText && !questionLatex) {
        box.textContent = "後端沒有提供題目內容。";
    }

    renderMath(box);
    updateQuestionDifficultyLabel();
}


/* ==================== 11. 步驟文字處理 ==================== */

function getStepText(step) {
    if (typeof step === "string") {
        return step;
    }

    return String(
        step.step_latex_template ||
        step.step_template ||
        step.content ||
        step.step_description ||
        step.description ||
        ""
    ).trim();
}

function getStepHint(step) {
    if (!step || typeof step !== "object") return "";

    return String(
        step.hint ||
        step.step_hint ||
        step.hint_text ||
        ""
    ).trim();
}

function renderCurrentStep() {
    const progress = getElement("step-progress");
    const progressBar = getElement("step-progress-bar");
    const currentStepLabel = getElement("current-step");

    const total = currentSteps.length;
    const completed = currentStepIndex;
    const current = Math.min(currentStepIndex + 1, total);

    if (progress) {
        progress.textContent =
            `第 ${current} / ${total} 步`;
    }

    if (progressBar) {
        progressBar.style.width =
            `${total ? completed / total * 100 : 0}%`;
    }

    if (currentStepLabel) {
        currentStepLabel.textContent =
            currentStepIndex < total
                ? `請選擇第 ${current} 步的正確解法。`
                : "所有步驟已完成。";
    }

    if (currentStepIndex >= total) {
        completeQuestion();
        return;
    }

    const step = currentSteps[currentStepIndex];
    const correctText = getStepText(step);

    if (!correctText) {
        showFeedback(
            `第 ${current} 步缺少標準解題內容，請檢查後端題庫。`,
            "error"
        );
        resetDoorArea();
        return;
    }

    currentChoices = buildChoices(step, correctText);
    renderDoors(currentChoices);
}


/* ==================== 12. 建立四個選項 ==================== */

/*
 * 後端建議格式：
 *
 * {
 *   "step_latex_template": "2x + 3x = 5x",
 *   "options": [
 *     {"text": "2x + 3x = 5x", "is_correct": true},
 *     {"text": "2x + 3x = 6x", "is_correct": false},
 *     {"text": "2x + 3x = 5x^2", "is_correct": false},
 *     {"text": "2x + 3x = 5", "is_correct": false}
 *   ],
 *   "hint": "合併同類項時，係數相加。"
 * }
 *
 * 沒有 options 時會使用暫時的干擾選項。
 * 暫時選項只供前端流程測試，不代表數學上一定合理。
 */

function shuffleArray(items) {
    const result = [...items];

    for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
    }

    return result;
}

function buildChoices(step, correctText) {
    const rawOptions = Array.isArray(step?.options)
        ? step.options
        : Array.isArray(step?.choices)
            ? step.choices
            : [];

    let choices = rawOptions.map(option => {
        if (typeof option === "string") {
            return {
                text: option,
                isCorrect: option.trim() === correctText.trim()
            };
        }

        return {
            text: String(
                option.text ??
                option.content ??
                option.latex ??
                ""
            ).trim(),
            isCorrect: Boolean(
                option.is_correct ??
                option.isCorrect ??
                option.correct
            )
        };
    }).filter(option => option.text);

    /*
     * 如果後端提供四個完整選項，
     * 就直接使用後端定義的正確選項。
     */
    if (
        choices.length === 4 &&
        choices.filter(choice => choice.isCorrect).length === 1
    ) {
        return shuffleArray(choices);
    }

    /*
     * 舊題庫尚未提供 options 時的暫時模式。
     * 從其他標準步驟中挑選不同文字作為干擾項。
     */
    choices = [{
        text: correctText,
        isCorrect: true
    }];

    const used = new Set([correctText.trim()]);

    currentSteps.forEach((otherStep, index) => {
        if (index === currentStepIndex) return;

        const text = getStepText(otherStep);
        if (!text || used.has(text)) return;

        used.add(text);

        choices.push({
            text,
            isCorrect: false
        });
    });

    /*
     * 選項不足四個時，加入明確標示為暫時測試的選項。
     * 正式題庫應改由後端提供有意義的錯誤解法。
     */
    const fallbackOptions = [
        "重新檢查運算順序，再進行計算。",
        "先檢查題目條件是否符合，再進行運算。",
        "重新整理目前的式子，確認每一步的等式關係。"
    ];

    for (const text of fallbackOptions) {
        if (choices.length >= 4) break;
        if (used.has(text)) continue;

        used.add(text);

        choices.push({
            text,
            isCorrect: false
        });
    }

    return shuffleArray(choices.slice(0, 4));
}


/* ==================== 13. 顯示四道門 ==================== */

function resetDoorArea() {
    const container = getElement("door-options");
    if (!container) return;

    container.replaceChildren();

    for (let i = 0; i < 4; i++) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "door-card";
        button.disabled = true;

        const number = document.createElement("span");
        number.className = "door-number";
        number.textContent = String(i + 1).padStart(2, "0");

        const icon = document.createElement("span");
        icon.className = "door-icon";
        icon.textContent = "🚪";

        const title = document.createElement("span");
        title.className = "door-title";
        title.textContent = "等待題目";

        const description = document.createElement("span");
        description.className = "door-description";
        description.textContent = "題目載入後顯示解題步驟";

        button.append(number, icon, title, description);
        container.appendChild(button);
    }
}

function renderDoors(choices) {
    const container = getElement("door-options");
    if (!container) return;

    container.replaceChildren();

    choices.forEach((choice, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "door-card";
        button.disabled = false;
        button.dataset.choiceIndex = String(index);

        const number = document.createElement("span");
        number.className = "door-number";
        number.textContent = String(index + 1).padStart(2, "0");

        const icon = document.createElement("span");
        icon.className = "door-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "🚪";

        const title = document.createElement("span");
        title.className = "door-title";
        title.textContent = `第 ${index + 1} 道門`;

        const description = document.createElement("span");
        description.className = "door-description";
        description.textContent = choice.text;

        button.append(number, icon, title, description);

        button.addEventListener("click", () => {
            chooseDoor(index);
        });

        container.appendChild(button);
    });

    renderMath(container);
}


/* ==================== 14. 選擇門 ==================== */

async function chooseDoor(choiceIndex) {
    if (
        !currentQuestion ||
        loadingQuestion ||
        gameFinished ||
        answerLocked ||
        abilityRequestInProgress
    ) {
        return;
    }

    const choice = currentChoices[choiceIndex];
    if (!choice) return;

    if (choice.isCorrect) {
        currentStepIndex++;

        showFeedback(
            `步驟 ${currentStepIndex} 正確！繼續前進。`,
            "success"
        );

        renderCurrentStep();
        return;
    }

    await handleWrongAnswer("這個解題步驟不正確，請再試一次。");
}


/* ==================== 15. Fuzzy 能力值 API ==================== */

async function applyFuzzyAbilityChange(
    isCorrect,
    remainingHP,
    elapsedTime,
    sessionId = gameSessionId
) {
    if (!currentQuestion) {
        throw new Error("目前沒有題目，無法計算能力值。");
    }

    const difficulty = Number(currentQuestion.difficulty) || DEFAULT_DIFFICULTY;
    const previousAbility = currentAbility;

    const payload = {
        remaining_hp: Math.max(
            0,
            Math.min(INITIAL_HP, Number(remainingHP) || 0)
        ),
        hint_count: Math.min(
            MAX_HINT_COUNT,
            Math.max(0, Number(currentHintCount) || 0)
        ),
        difficulty,
        elapsed_time: Math.max(0, Number(elapsedTime) || 0),
        is_correct: Boolean(isCorrect),
        current_ability: previousAbility
    };

    const response = await fetch(`${API_BASE}/api/ability/change`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const rawText = await response.text();
    let data;

    try {
        data = JSON.parse(rawText);
    } catch {
        throw new Error(
            `能力值 API 沒有回傳有效 JSON：${rawText.slice(0, 150)}`
        );
    }

    if (!response.ok) {
        throw new Error(
            data.message || data.error || `HTTP ${response.status}`
        );
    }

    if (
        data.status !== undefined &&
        data.status !== "success"
    ) {
        throw new Error(
            data.message || data.error || "Fuzzy 能力值計算失敗。"
        );
    }

    const newAbility = Number(data.new_ability);

    if (!Number.isFinite(newAbility)) {
        throw new Error("後端沒有回傳有效的 new_ability。");
    }

    const boundedAbility = Math.max(
        0,
        Math.min(MAX_ABILITY, newAbility)
    );

    if (sessionId !== gameSessionId) return null;

    data.ability_change =
        Math.round((boundedAbility - previousAbility) * 100) / 100;

    data.new_ability = boundedAbility;
    currentAbility = boundedAbility;

    updateStatus();

    return data;
}

function formatAbilityDelta(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) return "無法計算";

    const rounded = Math.round(number * 100) / 100;

    return rounded > 0 ? `+${rounded}` : String(rounded);
}


/* ==================== 16. 答錯與 HP 歸零 ==================== */

async function handleWrongAnswer(
    message = "解題步驟不正確。",
    fromTimeout = false
) {
    if (
        gameFinished ||
        loadingQuestion ||
        answerLocked ||
        abilityRequestInProgress ||
        !currentQuestion
    ) {
        return;
    }

    const sessionId = gameSessionId;

    answerLocked = true;
    stopTimer();

    currentHP = Math.max(0, currentHP - HP_LOSS);
    updateStatus();

    abilityRequestInProgress = true;
    let result;
    try {
        result = await applyFuzzyAbilityChange(false, currentHP, getElapsedTime(), sessionId);
    } catch (error) {
        if (sessionId !== gameSessionId || gameFinished) return;
        // HP penalty still applies if the ability service is unavailable.
        currentAbility = Math.max(0, currentAbility - 5);
        result = {ability_change: -5};
        console.error("能力值服務失敗，使用固定扣分：", error);
    }
    if (sessionId !== gameSessionId || gameFinished) return;
    abilityRequestInProgress = false;
    updateStatus();
    const penalty = `HP -${HP_LOSS}，能力值 ${formatAbilityDelta(result.ability_change)}。`;
    if (currentHP > 0) {
        showFeedback(`${fromTimeout ? "時間到！" : message} ${penalty}請重新選擇目前步驟。`, "error");
        answerLocked = false;
        if (fromTimeout) remainingTime = currentQuestionTime;
        updateStatus();
        startTimer();
        return;
    }
    currentHP = INITIAL_HP;
    updateStatus();
    const feedback = `${penalty} HP 歸零，恢復至 ${INITIAL_HP}，目前能力值 ${currentAbility}。`;

    if (currentAbility >= PASS_ABILITY) {
        abilityRequestInProgress = false;
        finishGame(
            `${feedback} 能力值已達通關門檻 ${PASS_ABILITY}。`
        );
        return;
    }

    showFeedback(
        `${feedback} 正在重生並載入新題目。`,
        "error"
    );

    nextQuestionTimeoutId = window.setTimeout(() => {
        nextQuestionTimeoutId = null;

        if (sessionId !== gameSessionId || gameFinished) return;

        abilityRequestInProgress = false;
        answerLocked = false;

        loadNextQuestion();
    }, 1000);
}


/* ==================== 17. 完成整道題目 ==================== */

async function completeQuestion() {
    if (
        gameFinished ||
        answerLocked ||
        abilityRequestInProgress ||
        !currentQuestion
    ) {
        return;
    }

    answerLocked = true;
    stopTimer();

    const sessionId = gameSessionId;
    const elapsedTime = getElapsedTime();
    const remainingHP = currentHP;

    abilityRequestInProgress = true;

    let fuzzyResult;

    try {
        fuzzyResult = await applyFuzzyAbilityChange(
            true,
            remainingHP,
            elapsedTime,
            sessionId
        );
    } catch (error) {
        console.error("答對後能力值計算失敗：", error);

        if (sessionId !== gameSessionId) return;

        abilityRequestInProgress = false;
        answerLocked = false;

        showFeedback(
            `步驟全部完成，但能力值計算失敗：${error.message}`,
            "error"
        );

        startTimer();
        return;
    }

    if (
        sessionId !== gameSessionId ||
        gameFinished ||
        !fuzzyResult
    ) {
        return;
    }

    currentMP = Math.min(
        INITIAL_MP,
        currentMP + MP_RECOVERY
    );

    updateStatus();

    const message =
        `恭喜！全部 ${currentSteps.length} 個步驟完成。` +
        `能力值 ${formatAbilityDelta(fuzzyResult.ability_change)}，` +
        `目前能力值 ${currentAbility}。MP +${MP_RECOVERY}。`;

    if (currentAbility >= PASS_ABILITY) {
        finishGame(
            `${message} 已達通關門檻 ${PASS_ABILITY}！`
        );
        return;
    }

    showFeedback(message, "success");

    nextQuestionTimeoutId = window.setTimeout(() => {
        nextQuestionTimeoutId = null;

        if (sessionId !== gameSessionId || gameFinished) return;

        abilityRequestInProgress = false;
        answerLocked = false;

        loadNextQuestion();
    }, 1200);
}


/* ==================== 18. 遊戲結束 ==================== */

function finishGame(message) {
    gameFinished = true;
    answerLocked = true;
    abilityRequestInProgress = false;

    stopTimer();
    clearNextQuestionTimeout();

    showFeedback(message, "success");
}


/* ==================== 19. 提示功能 ==================== */

function useHint() {
    if (
        !currentQuestion ||
        gameFinished ||
        answerLocked ||
        abilityRequestInProgress
    ) {
        showFeedback("目前無法使用提示。");
        return;
    }

    if (currentStepIndex >= currentSteps.length) {
        showFeedback("目前沒有需要提示的步驟。");
        return;
    }

    if (currentMP < HINT_MP_COST) {
        showFeedback("MP 不足，無法使用提示。", "error");
        return;
    }

    if (currentHintCount >= MAX_HINT_COUNT) {
        showFeedback(
            `本題提示次數已達上限 ${MAX_HINT_COUNT} 次。`,
            "error"
        );
        return;
    }

    const step = currentSteps[currentStepIndex];
    const hint = getStepHint(step);

    if (!hint) {
        showFeedback(
            "這個步驟尚未設定提示，請在題庫中補上 hint 欄位。",
            "error"
        );
        return;
    }

    currentMP -= HINT_MP_COST;
    currentHintCount++;

    updateStatus();

    showFeedback(
        `提示：${hint}（本題已使用 ${currentHintCount} 次提示）`,
        "info"
    );
}


/* ==================== 20. 倒數計時 ==================== */

function startTimer() {
    stopTimer();

    if (
        gameFinished ||
        !currentQuestion ||
        answerLocked ||
        abilityRequestInProgress
    ) {
        return;
    }

    timerId = window.setInterval(() => {
        if (
            gameFinished ||
            !currentQuestion ||
            answerLocked ||
            abilityRequestInProgress
        ) {
            stopTimer();
            return;
        }

        remainingTime = Math.max(0, remainingTime - 1);
        updateStatus();

        if (remainingTime <= 0) {
            stopTimer();
            handleWrongAnswer("時間到！", true);
        }
    }, 1000);
}

function stopTimer() {
    if (timerId !== null) {
        window.clearInterval(timerId);
        timerId = null;
    }
}


/* ==================== 21. 初始化 ==================== */

function initializeGame() {
    updateStatus();
    resetDoorArea();

    showPage("home-page");

    console.log("FuzzyMathGame 四道門路徑選擇版已載入。");
}

document.addEventListener("DOMContentLoaded", initializeGame);
