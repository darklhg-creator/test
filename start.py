import FinanceDataReader as fdr
from pykrx import stock
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import sys

# ==========================================
# 0. 사용자 설정
# ==========================================
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

KST = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST)
TARGET_DATE = CURRENT_KST.strftime("%Y%m%d") # pykrx용 포맷

def send_discord_message(content):
    try:
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': content})
    except Exception as e:
        print(f"전송 실패: {e}")

def main():
    # 2026-02-26 목요일 체크 및 휴장일 확인
    print(f"[{CURRENT_KST.strftime('%Y-%m-%d')}] 분석 시작")
    if CURRENT_KST.weekday() >= 5:
        print("⏹️ 주말입니다.")
        return

    try:
        # 1. pykrx로 전 종목 EPS(투자지표) 미리 가져오기
        # 이 데이터에 EPS가 들어있습니다.
        df_fund = stock.get_market_fundamental(TARGET_DATE)
        
        # 2. 분석 대상 종목 확보 (코스피 300 + 코스닥 500)
        df_kospi = fdr.StockListing('KOSPI').head(300)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(500)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        all_analyzed = []
        print(f"📡 {len(df_total)}개 종목 이격도 및 EPS 분석 중...")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            try:
                # 이격도 계산
                df_price = fdr.DataReader(code).tail(30)
                if len(df_price) < 20: continue
                
                current_price = df_price['Close'].iloc[-1]
                ma20 = df_price['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((current_price / ma20) * 100, 1)

                # EPS 데이터 매칭 (데이터가 없으면 0으로 표시)
                eps_val = 0
                if code in df_fund.index:
                    eps_val = df_fund.loc[code, 'EPS']

                # 이격도 95% 이하인 것들 수집
                if disparity <= 95.0:
                    all_analyzed.append({
                        'name': name,
                        'disparity': disparity,
                        'eps': eps_val,
                        'code': code
                    })
            except:
                continue

        # 3. 결과 정렬 (이격도 낮은 순)
        results = sorted(all_analyzed, key=lambda x: x['disparity'])[:50]

        if results:
            report = f"### 📊 이격도 & EPS 분석 리포트 (TOP 50)\n"
            report += f"기준일: {CURRENT_KST.strftime('%Y-%m-%d')}\n"
            report += "格式: **종목명** | 이격도 | **EPS**\n"
            report += "---"
            
            for r in results:
                # EPS가 0 이하이면 (적자) 표시를 위해 강조하거나 그대로 표시
                eps_str = f"{int(r['eps']):,}" if r['eps'] > 0 else f"**{int(r['eps']):,} (적자)**"
                report += f"\n· **{r['name']}**: {r['disparity']}% | EPS: {eps_str}"

            report += "\n\n" + "="*30
            report += "\n📝 **[판단 가이드]**"
            report += "\n1. EPS가 플러스(+)인 종목 중 이격도가 낮은 것을 우선 보세요."
            report += "\n2. EPS가 마이너스(-)라면 최근 뉴스에서 '흑자전환' 소식이 있는지 확인하세요."
            
            send_discord_message(report)
            print("✅ 분석 완료 및 전송 성공!")
        else:
            send_discord_message("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        send_discord_message(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    main()
