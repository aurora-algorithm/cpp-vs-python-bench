@echo off
rem Builds the C++ programs natively on Windows: clang++ (LLVM) against the MSVC runtime and SDK.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set PATH=C:\Program Files\LLVM\bin;C:\Program Files\CMake\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%
cd /d "%~dp0"
cmake -S cpp -B cpp\build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ || exit /b 1
cmake --build cpp\build || exit /b 1
for %%f in (tools\opencv\build\x64\vc16\bin\opencv_world*.dll tools\opencv\build\x64\vc17\bin\opencv_world*.dll) do copy /y "%%f" cpp\build >nul
clang++ -std=c++20 -O3 -march=native -DNDEBUG -g -S -masm=intel -fno-asynchronous-unwind-tables -o cpp\build\shrink_loop.s cpp\src\shrink_loop.cpp || exit /b 1
