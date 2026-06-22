"""
☕ 축구 승률 커피내기 미니게임
--------------------------------
팀원들끼리 "이 경기 누가 이길까?"를 맞추고,
틀린 사람이 커피를 사는 미니게임입니다.

- 외부 라이브러리 설치 불필요 (Python 기본 내장 tkinter만 사용)
- 코드는 "1. 데이터 -> 2. 계산 로직 -> 3. 저장 -> 4. 화면(GUI) -> 5. 실행"
  순서로 나눠져 있어서, 위에서부터 천천히 읽으면 흐름을 따라갈 수 있습니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
import json
import os
from datetime import datetime


# =========================================================
# 1. 기본 데이터 정의
# =========================================================

# 팀별 "전력 점수"를 미리 정해두고, 이 점수로 승률을 계산합니다.
# 숫자가 높을수록 강팀입니다. 우리 회사 풋살팀 이름으로 바꿔도 됩니다!
TEAM_POWER = {
    "대한민국": 78,
    "일본": 75,
    "독일": 88,
    "브라질": 90,
    "아르헨티나": 89,
    "스페인": 85,
    "사우디아라비아": 60,
    "우리회사_개발팀": 55,
    "우리회사_영업팀": 50,
}

SAVE_FILE = "coffee_bet_history.json"  # 내기 결과를 저장해 둘 파일 이름


# =========================================================
# 2. 승률 계산 / 경기 시뮬레이션 로직
#    (화면 코드와 분리해두면 나중에 테스트하거나 재사용하기 쉽습니다)
# =========================================================

def calculate_win_rate(team_a: str, team_b: str):
    """
    두 팀의 전력 점수로 각 팀의 승률(%)을 계산합니다.
    공식은 아주 단순합니다: 내 전력 / (내 전력 + 상대 전력) * 100
    """
    power_a = TEAM_POWER[team_a]
    power_b = TEAM_POWER[team_b]
    total_power = power_a + power_b

    win_rate_a = round(power_a / total_power * 100, 1)
    win_rate_b = round(100 - win_rate_a, 1)
    return win_rate_a, win_rate_b


def simulate_match(team_a: str, team_b: str):
    """
    승률에 맞춰 실제 경기 결과를 무작위로 정합니다.
    0~100 사이 랜덤 숫자를 뽑아서, 그 숫자가 team_a 승률보다 작으면 team_a 승리.
    (승률이 높을수록 그 구간이 넓어서 이길 확률이 더 높아지는 원리입니다)
    """
    win_rate_a, win_rate_b = calculate_win_rate(team_a, team_b)
    random_number = random.uniform(0, 100)

    winner = team_a if random_number < win_rate_a else team_b
    return winner, win_rate_a, win_rate_b


# =========================================================
# 3. 내기 기록을 파일로 저장하고 불러오는 함수들
#    (프로그램을 껐다 켜도 지난 커피 내기 기록이 남아있게 하기 위함)
# =========================================================

def load_history():
    """저장된 내기 기록을 불러옵니다. 파일이 없으면 빈 리스트를 줍니다."""
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history):
    """현재까지의 내기 기록을 파일에 저장합니다."""
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_record(history, players_bets: dict, winner: str, coffee_buyers: list):
    """
    한 번의 내기 결과를 기록 리스트에 추가하고 파일에 저장합니다.
    players_bets 예시: {"철수": "대한민국", "영희": "일본"}
    """
    record = {
        "날짜": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "참가자_예측": players_bets,
        "실제_승리팀": winner,
        "커피_사는_사람들": coffee_buyers,
    }
    history.append(record)
    save_history(history)
    return history


# =========================================================
# 4. 화면(GUI) 구성
#    버튼을 누르면 위에서 만든 함수들을 호출하는 방식입니다.
# =========================================================

class CoffeeBetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("☕ 축구 승률 커피내기")
        self.root.geometry("420x580")

        self.history = load_history()   # 과거 기록 불러오기
        self.players = []                # 등록된 참가자 이름 목록

        # 화면을 4개 영역으로 나눠서 차례로 만듭니다.
        self.build_team_select_section()
        self.build_player_section()
        self.build_action_section()
        self.build_log_section()

    # ---- 4-1. 팀 선택 영역 ----
    def build_team_select_section(self):
        frame = ttk.LabelFrame(self.root, text="① 경기 팀 선택")
        frame.pack(fill="x", padx=10, pady=5)

        team_names = list(TEAM_POWER.keys())

        ttk.Label(frame, text="팀 A:").grid(row=0, column=0, padx=5, pady=5)
        self.team_a_var = tk.StringVar(value=team_names[0])
        ttk.Combobox(
            frame, textvariable=self.team_a_var, values=team_names,
            state="readonly", width=16
        ).grid(row=0, column=1)

        ttk.Label(frame, text="팀 B:").grid(row=1, column=0, padx=5, pady=5)
        self.team_b_var = tk.StringVar(value=team_names[1])
        ttk.Combobox(
            frame, textvariable=self.team_b_var, values=team_names,
            state="readonly", width=16
        ).grid(row=1, column=1)

        ttk.Button(
            frame, text="승률 계산하기", command=self.show_win_rate
        ).grid(row=2, column=0, columnspan=2, pady=5)

        self.win_rate_label = ttk.Label(frame, text="승률: -", font=("맑은 고딕", 10, "bold"))
        self.win_rate_label.grid(row=3, column=0, columnspan=2, pady=5)

    def show_win_rate(self):
        team_a = self.team_a_var.get()
        team_b = self.team_b_var.get()

        if team_a == team_b:
            messagebox.showwarning("선택 오류", "서로 다른 두 팀을 선택해주세요!")
            return

        win_rate_a, win_rate_b = calculate_win_rate(team_a, team_b)
        self.win_rate_label.config(text=f"{team_a} {win_rate_a}%  vs  {team_b} {win_rate_b}%")

    # ---- 4-2. 참가자 등록 영역 ----
    def build_player_section(self):
        frame = ttk.LabelFrame(self.root, text="② 참가자 등록 (몰래 같이할 동료들)")
        frame.pack(fill="x", padx=10, pady=5)

        self.player_name_entry = ttk.Entry(frame, width=16)
        self.player_name_entry.grid(row=0, column=0, padx=5, pady=5)

        ttk.Button(frame, text="추가", command=self.add_player).grid(row=0, column=1, padx=5)

        self.player_list_label = ttk.Label(frame, text="참가자: (없음)")
        self.player_list_label.grid(row=1, column=0, columnspan=2, pady=5)

    def add_player(self):
        name = self.player_name_entry.get().strip()
        if not name:
            return  # 빈 칸이면 그냥 무시
        if name in self.players:
            messagebox.showinfo("알림", "이미 등록된 이름이에요.")
            return

        self.players.append(name)
        self.player_name_entry.delete(0, tk.END)
        self.player_list_label.config(text="참가자: " + ", ".join(self.players))

    # ---- 4-3. 베팅 입력 + 경기 시뮬레이션 영역 ----
    def build_action_section(self):
        frame = ttk.LabelFrame(self.root, text="③ 베팅하고 결과 확인하기")
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(frame, text="베팅 입력창 열기", command=self.open_bet_window).pack(pady=5)

    def open_bet_window(self):
        """참가자별로 누가 이길지 베팅하는 작은 팝업창을 엽니다."""
        team_a = self.team_a_var.get()
        team_b = self.team_b_var.get()

        if team_a == team_b:
            messagebox.showwarning("선택 오류", "먼저 서로 다른 두 팀을 선택해주세요!")
            return
        if len(self.players) == 0:
            messagebox.showwarning("참가자 없음", "먼저 참가자를 등록해주세요!")
            return

        bet_window = tk.Toplevel(self.root)
        bet_window.title("누가 이길지 베팅하세요")
        bet_window.geometry(f"300x{80 + 40 * len(self.players)}")

        bet_vars = {}  # {참가자 이름: 선택한 팀을 담는 tkinter 변수}

        for i, player in enumerate(self.players):
            ttk.Label(bet_window, text=f"{player}님의 예측:").grid(row=i, column=0, padx=5, pady=5)
            var = tk.StringVar(value=team_a)
            ttk.Combobox(
                bet_window, textvariable=var, values=[team_a, team_b],
                state="readonly", width=14
            ).grid(row=i, column=1)
            bet_vars[player] = var

        def confirm_bets():
            # 참가자별로 선택한 팀을 일반 딕셔너리로 정리해서 다음 단계로 넘깁니다.
            bets = {player: var.get() for player, var in bet_vars.items()}
            bet_window.destroy()
            self.run_match(team_a, team_b, bets)

        ttk.Button(
            bet_window, text="베팅 확정하고 경기 시작!", command=confirm_bets
        ).grid(row=len(self.players), column=0, columnspan=2, pady=10)

    def run_match(self, team_a, team_b, bets):
        """경기를 시뮬레이션하고, 누가 커피를 사야 하는지 보여줍니다."""
        winner, win_rate_a, win_rate_b = simulate_match(team_a, team_b)

        # 예측이 틀린 사람 = 커피를 사야 하는 사람
        coffee_buyers = [p for p, pick in bets.items() if pick != winner]
        correct_players = [p for p, pick in bets.items() if pick == winner]

        self.history = add_record(self.history, bets, winner, coffee_buyers)

        result_msg = (
            f"⚽ 경기 결과: {winner} 승리!  (승률 {win_rate_a}% vs {win_rate_b}%)\n\n"
            f"🎉 맞춘 사람: {', '.join(correct_players) if correct_players else '없음'}\n"
            f"☕ 커피 사야 하는 사람: {', '.join(coffee_buyers) if coffee_buyers else '없음'}"
        )
        messagebox.showinfo("경기 결과 발표", result_msg)
        self.refresh_log()

    # ---- 4-4. 지난 기록 보여주는 영역 ----
    def build_log_section(self):
        frame = ttk.LabelFrame(self.root, text="④ 커피 내기 기록 (최근 10개)")
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = tk.Text(frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.refresh_log()

    def refresh_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)

        if not self.history:
            self.log_text.insert(tk.END, "아직 기록이 없습니다.")
        else:
            for record in reversed(self.history[-10:]):
                buyers = ", ".join(record["커피_사는_사람들"]) if record["커피_사는_사람들"] else "없음"
                line = f"[{record['날짜']}] 승리팀: {record['실제_승리팀']} | 커피 사는 사람: {buyers}\n"
                self.log_text.insert(tk.END, line)

        self.log_text.config(state="disabled")


# =========================================================
# 5. 프로그램 실행
#    이 파일을 다른 프로그램에 합칠 때는, 아래 main()을 호출하는 부분만
#    기존 메인 코드의 "메뉴" 또는 "버튼"에 연결해주면 됩니다.
# =========================================================

def main():
    root = tk.Tk()
    CoffeeBetApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
