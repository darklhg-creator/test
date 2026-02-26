import FinanceDataReader as fdr
from pykrx import stock
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import time

# ==========================================
# 0. 사용자 설정
# ==========================================
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

KST = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST)
TARGET_DATE = CURRENT_KST.strftime("%Y%m%d") 

def send_discord_message(content):
    """디스코드 메시지 전송 (안정성을 위해 2000자 단위 체크)"""
    try:
        if len(content) > 1900:
            parts = [content[i:i+1900] for i in range(0, len(content), 1900)]
            for part in parts:
                requests.post(IGYEOK_WEBHOOK_URL, json={'content': part})
                time.sleep(0.5)
        else:
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': content})
    except Exception as e:
        print(f"전송 실패: {e}")

def main():
    print(f"[{CURRENT_KST.strftime('%Y-%m-%d')}] 분석 시작 (TOP 30)")
    if CURRENT_KST.weekday() >= 5:
        print("⏹️ 주말 휴장일입니다.")
        return

    try:
        # 1. 투자지표 데이터 가져오기
        df_fund = stock.get_market_fundamental(TARGET_DATE)
        
        # 2. 분석 대상 (코스피 300 + 코스닥 500)
        df_kospi = fdr.StockListing('KOSPI').head(300)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(500)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        all_analyzed = []
        print(f"📡 {len(df_total)}개 종목 이격도 분석 중...")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            try:
                df_price = fdr.DataReader(code).tail(30)
                if len(df_price) < 20: continue
                
                current_price = df_price['Close'].iloc[-1]
                ma20 = df_price['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((current_price / ma20) * 100, 1)

                # EPS 데이터 매칭
                eps_val = 0
                if code in df_fund.index:
                    eps_val = df_fund.loc[code, 'EPS']

                # 이격도 95% 이하 종목 수집
                if disparity <= 95.0:
                    all_analyzed.append({
                        'name': name,
                        'disparity': disparity,
                        'eps': eps_val,
                        'code': code
                    })
            except:
                continue

        # 3. 결과 정렬 및 30개 추출
        # 정렬 우선순위: 1. 흑자 여부(EPS > 0), 2. 이격도 낮은 순
        results = sorted(all_analyzed, key=lambda x: (x['eps'] <= 0, x['disparity']))[:30]

        if results:
            report = f"### 📊 [2026-02-26] 이격도 & EPS 분석 (TOP 30)\n"
            report += "💡 **알림**: 흑자(EPS > 0) 종목이 상단에 배치되었습니다.\n"
            report += "---"
            
            for r in results:
                # 적자 종목(EPS <= 0)은 강조 표시
                eps_str = f"{int(r['eps']):,}" if r['eps'] > 0 else f"**{int(r['eps']):,} (적자)**"
                report += f"\n· **{r['name']}**: {r['disparity']}% | EPS: {eps_str}"

            report += "\n\n" + "="*30
            report += "\n📝 **[매매 참고]**"
            report += "\n- 이격도 90 이하이면서 흑자인 종목을 최우선으로 검토하세요."
            report += "\n- 최근 상승세가 좋은 테마인지 뉴스를 병행 확인하세요."
            
            send_discord_message(report)
            print("✅ TOP 30 분석
