@echo off
REM Chay crawler lay phu de moi, roi push len GitHub (neu co thay doi).
REM Dat lich bang Task Scheduler de tu dong chay moi toi.
cd /d %~dp0
python crawl_phuc.py
if errorlevel 1 (
  echo Crawler loi hoac bi chan, dung lai.
  exit /b 1
)
git add data.json
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Cap nhat phu de %date%"
  git push
) else (
  echo Khong co video moi.
)
pause
