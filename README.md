# PROJECT RIGCHECK: Master Documentation & Blueprint

## 1. Executive Summary

**RigCheck** is a 100% local, AI-powered video game recommendation engine designed to run entirely on the user's hardware (optimized for Lenovo LOQ class laptops).

- **Core Purpose:** To perfectly match a user’s desired **Vibe** (abstract concept), **Wallet** (strict budget), and **Rig** (hardware capability).
- **Engineering Constraint:** Zero external API calls. Must operate within local VRAM limits without crashing during generation.

---

## 2. Technical Stack

- **LLM Brain:** Mistral-7B Instruct.
- **LLM Hosting:** Ollama (serving the model locally).
- **Core Logic:** Python.
- **Data Handling:** Pandas (Strict tabular operations).
- **Search Algorithm:** BM25 (Weighted keyword ranking).
- **Dataset:** Local `.csv` file with a pre-processed column `Vibe_Text` (merging `Tags` + `Description`).

---

## 3. Core Architecture: "Two-Stage Hybrid"

We explicitly **rejected traditional Vector RAG** (ChromaDB/Embeddings) because embeddings eat limited VRAM, overcomplicate the logic, and are unnecessary for small-to-medium CSV datasets.

We are implementing a **Two-Stage Hybrid** approach:

1. **Stage 1 (Python):** Blazing-fast, mathematically precise traditional search and filtering (BM25 + Pandas).
2. **Stage 2 (Mistral-7B):** Context-aware conversational summary of the final filtered results.

---

## 4. Conversation Workflow (State Management)

We use a **Linear State Machine** approach. The conversation follows a hardcoded path enforced by Python to ensure all required data is collected.

- **Session Memory:** Handled by a simple Python list: `chat_history = []`.
- **State Variables (The User Profile):**
    - `user_vibe` (String)
    - `user_budget` (Integer - INR)
    - `user_specs` (Hardware Tier 1-5)

---

## 5. The 3-Level Funnel (Detailed Breakdown)

This sequence of operations runs when the conversation workflow moves into processing mode.

### Level 1: The Vibe Check

- **Input:** User text prompt.
- **Method:** **BM25 Search Algorithm** (Scoring/Weighted Ranking).
- **Action:** Scans the `.csv['Vibe_Text']` column. Scores games based on keyword frequency and rarity (IDF).
- **Outcome:** Reduces the dataset from 10,000+ games down to the **Top 15** highest vibe matches.

### Level 2: The Wallet Check

- **Input:** `user_budget` (extracted integer).
- **Method:** Pure **Pandas Data Frame Filtering** (Boolean).
- **Action:** Runs a strict binary check against the Top 15 list (`Price_INR <= user_budget`).
- **Outcome:** Reduces the **Top 15** list down to the **Top 5** affordable games.

### Level 3: The Rig Check

- **Input:** `user_specs` (Hardware Tier).
- **Method:** **The Tier System** abstraction (Math).
- **Action:** Binary comparison (`Game_Min_Tier <= user_specs_tier`). Hard constraint: `MAX_OUTPUT = 2-3` (implemented via `.head(3)`).
- **Outcome:** Reduces the **Top 5** down to the **Final 2 playable games**.

---

## 6. Brainstorming Edge Cases & Solutions

These are the "fuzzle-proofing" protocols we designed:

1. **The Cold Start:** If the user doesn't know what vibe they want, the bot presents "Vibe Starter Packs" (e.g., Epic Fantasy, Gritty Noir, Cozy Farming).
2. **The Abstract Query:** If a query is too complex (e.g., "A game where I can feel the rain"), the LLM is first used to rewrite the prompt into optimized keywords before running Level 1 (BM25).
3. **The Diversity Rule:** The Final 2 output ensures recommendations aren't just from the same franchise.
4. **The Local Bottleneck (Why only 2-3 final games?):** To keep conversational response generation under 1 minute and avoid VRAM crashes, we strictly limit the amount of text sent to Mistral-7B for summarization. The assistant focuses on curation over quantity for a premium UX.

---

## 7. The Golden Rule

> **"MATH FIRST, VIBE SECOND."**
> 
> 
> You shall never ask the LLM to calculate budgets or predict hardware frame rates. Python handles the cold, hard numbers and logical filtering. The LLM is used only at the very end to summarize descriptions and provide personality.
