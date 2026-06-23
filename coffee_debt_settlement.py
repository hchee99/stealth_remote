"""
☕ 누적 커피 빚 정산판
--------------------------------
coffee_bet_game.py 에서 쌓인 "coffee_bet_history.json" 기록을 읽어와서
- 누가 내기에 몇 번 참여했는지
- 누가 몇 번 맞췄는지 (적중률)
- 누가 커피를 몇 잔 사야 하는지 (누적 빚)
을 한눈에 보여주고, "정산 완료" 버튼으로 빚을 갚은 걸로 처리하는 프로그램입니다.

- coffee_bet_game.py와 같은 폴더에 두고 실행하세요. (같은 기록 파일을 읽습니다)
- 외부 라이브러리 설치 불필요 (Python 기본 내장 tkinter만 사용)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os


# =========================================================
# 1. 파일 경로 정의
# =========================================================

HISTORY_FILE = "coffee_bet_history.json"      # coffee_bet_game.py가 만드는 내기 기록 파일
SETTLEMENT_FILE = "coffee_settlement.json"     # 이 프로그램이 만드는 "이미 정산한 커피 잔 수" 파일


# =========================================================
# 2. 데이터 불러오기 / 저장하기
#    (파일이 없을 때도 에러 없이 빈 값으로 시작하도록 처리)
# =========================================================

def load_history():
    """내기 기록을 불러옵니다. 파일이 없으면 빈 리스트를 줍니다."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_settlement():
    """이미 정산(커피를 실제로 사서 갚음 처리)한 횟수를 불러옵니다.
    형태: {"철수": 2, "영희": 0} -> 철수는 이미 커피 2잔을 사서 정산함
    """
    if os.path.exists(SETTLEMENT_FILE):
        with open(SETTLEMENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_settlement(settlement: dict):
    """정산 기록을 파일에 저장합니다."""
    with open(SETTLEMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(settlement, f, ensure_ascii=False, indent=2)


# =========================================================
# 3. 통계 계산 로직
#    (화면 코드와 분리해두면 나중에 테스트하기 쉽습니다)
# =========================================================

def calculate_player_stats(history: list, settlement: dict):
    """
    내기 기록 전체를 한 명씩 집계해서 아래 정보를 담은 딕셔너리를 만듭니다.

    결과 형태:
    {
        "철수": {
            "참여횟수": 5,
            "맞춘횟수": 3,
            "적중률": 60.0,
            "총_커피_빚": 2,      # 내기에서 진 횟수 (커피를 사야 했던 횟수)
            "이미_정산": 1,       # 실제로 갚은 횟수
            "남은_빚": 1,         # 아직 안 갚은 횟수 = 총_커피_빚 - 이미_정산
        },
        ...
    }
    """
    stats = {}  # 참가자 이름을 key로 쓰는 딕셔너리

    for record in history:
        coffee_buyers = record["커피_사는_사람들"]       # 이 경기에서 진(=커피 사야 하는) 사람들 목록
        player_predictions = record["참가자_예측"]       # coffee_bet_game.py가 저장할 때 쓰는 키 이름

        for player in player_predictions:
            # 처음 등장하는 참가자는 통계 칸을 0으로 미리 만들어 둡니다.
            if player not in stats:
                stats[player] = {"참여횟수": 0, "맞춘횟수": 0, "총_커피_빚": 0}

            stats[player]["참여횟수"] += 1

            if player in coffee_buyers:
                stats[player]["총_커피_빚"] += 1
            else:
                stats[player]["맞춘횟수"] += 1

    # 적중률, 이미 정산한 횟수, 남은 빚을 마지막에 한 번에 채워 넣습니다.
    for player, info in stats.items():
        info["적중률"] = round(info["맞춘횟수"] / info["참여횟수"] * 100, 1) if info["참여횟수"] > 0 else 0.0
        info["이미_정산"] = settlement.get(player, 0)
        info["남은_빚"] = info["총_커피_빚"] - info["이미_정산"]

    return stats


# =========================================================
# 4. 화면(GUI) 구성
# =========================================================

class SettlementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("☕ 누적 커피 빚 정산판")
        self.root.geometry("560x420")

        self.build_top_section()
        self.build_table_section()
        self.build_bottom_section()

        self.refresh_table()  # 시작하면 바로 한 번 불러와서 보여줍니다.

    # ---- 4-1. 상단 안내 + 새로고침 버튼 ----
    def build_top_section(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            frame,
            text="누가 커피를 몇 잔 빚지고 있는지 보여줍니다. (적중률 낮은 사람이 빚이 많아요 😉)",
            wraplength=520,
        ).pack(side="left")

        ttk.Button(frame, text="🔄 새로고침", command=self.refresh_table).pack(side="right")

    # ---- 4-2. 랭킹 표 ----
    def build_table_section(self):
        columns = ("이름", "참여횟수", "적중률(%)", "총_커피_빚", "이미_정산", "남은_빚")

        self.table = ttk.Treeview(self.root, columns=columns, show="headings", height=12)
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=80, anchor="center")
        self.table.column("이름", width=100)

        self.table.pack(fill="both", expand=True, padx=10, pady=5)

    # ---- 4-3. 정산 완료 처리 영역 ----
    def build_bottom_section(self):
        frame = ttk.Frame(self.root)
        frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame, text="표에서 이름을 클릭한 뒤 ↓").pack(side="left", padx=(0, 5))
        ttk.Button(
            frame, text="☕ 커피 1잔 정산 완료 처리", command=self.settle_one_coffee
        ).pack(side="left")

    # ---- 핵심 동작: 표 새로 그리기 ----
    def refresh_table(self):
        history = load_history()
        settlement = load_settlement()
        stats = calculate_player_stats(history, settlement)

        # 기존 표 내용을 지우고 다시 채웁니다.
        for row in self.table.get_children():
            self.table.delete(row)

        # 남은 빚이 많은 사람이 위로 오도록 정렬해서 보여줍니다.
        sorted_players = sorted(stats.items(), key=lambda item: item[1]["남은_빚"], reverse=True)

        for player, info in sorted_players:
            self.table.insert(
                "", "end",
                values=(
                    player,
                    info["참여횟수"],
                    info["적중률"],
                    info["총_커피_빚"],
                    info["이미_정산"],
                    info["남은_빚"],
                ),
            )

    # ---- 핵심 동작: 정산 완료 처리 ----
    def settle_one_coffee(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("선택 필요", "표에서 정산할 사람을 먼저 클릭해주세요!")
            return

        # 선택한 줄의 첫 번째 칸(이름)을 가져옵니다.
        player_name = self.table.item(selected[0])["values"][0]

        settlement = load_settlement()
        settlement[player_name] = settlement.get(player_name, 0) + 1
        save_settlement(settlement)

        messagebox.showinfo("정산 완료", f"{player_name}님의 커피 1잔이 정산 완료 처리되었습니다 ☕✅")
        self.refresh_table()


# =========================================================
# 5. 프로그램 실행
# =========================================================

def main():
    root = tk.Tk()
    SettlementApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
