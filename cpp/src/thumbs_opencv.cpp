// Test 2: turn every JPEG in a folder into a WebP thumbnail, 512 px on its long edge, with OpenCV.
// usage: thumbs_opencv IN_DIR OUT_DIR
// STAGES_OUT, when set, gets decode / resize / encode seconds per photo.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>

#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include "common.hpp"

constexpr int SIZE = 512;
constexpr int QUALITY = 80;

int main(int argc, char** argv) {
  if (argc < 3) { std::cerr << "usage: thumbs_opencv IN_DIR OUT_DIR\n"; return 2; }
  const bench::fs::path dst = argv[2];
  bench::fs::create_directories(dst);
  cv::setNumThreads(1);
  bench::Progress progress;
  std::FILE* stages = std::getenv("STAGES_OUT") ? std::fopen(std::getenv("STAGES_OUT"), "w") : nullptr;
  if (stages) std::fprintf(stages, "file\tdecode\tresize\tencode\n");
  using clock = std::chrono::steady_clock;
  const auto secs = [](clock::time_point a, clock::time_point b) { return std::chrono::duration<double>(b - a).count(); };
  long done = 0;
  for (const auto& path : bench::photos(argv[1])) {
    const auto t0 = clock::now();
    cv::Mat img = cv::imread(path.string(), cv::IMREAD_COLOR);
    if (img.empty()) { std::cerr << path << ": cannot read\n"; return 1; }
    const auto t1 = clock::now();
    const bench::Size s = bench::thumb_size(img.cols, img.rows, SIZE);
    cv::Mat small;
    cv::resize(img, small, cv::Size(s.w, s.h), 0, 0, cv::INTER_AREA);
    const auto t2 = clock::now();
    const std::string out = (dst / (path.stem().string() + ".webp")).string();
    const bool ok = cv::imwrite(out, small, {cv::IMWRITE_WEBP_QUALITY, QUALITY});
    if (!ok) { std::cerr << out << ": cannot write\n"; return 1; }
    const auto t3 = clock::now();
    if (stages) std::fprintf(stages, "%s\t%.6f\t%.6f\t%.6f\n", path.filename().string().c_str(), secs(t0, t1), secs(t1, t2), secs(t2, t3));
    progress.tick(++done);
  }
  if (stages) std::fclose(stages);
  return 0;
}
