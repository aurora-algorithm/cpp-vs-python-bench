// Shared by the C++ programs: the photo list, the thumbnail size rule and the progress log.
#pragma once
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

namespace bench {

namespace fs = std::filesystem;

inline std::vector<fs::path> photos(const fs::path& dir) {
  std::vector<fs::path> out;
  for (const auto& e : fs::directory_iterator(dir)) {
    if (e.path().extension() == ".jpg") out.push_back(e.path());
  }
  std::sort(out.begin(), out.end());
  return out;
}

// Pillow's Image.thumbnail size rule, so every program writes thumbnails of the same size: fit inside
// box x box and round the short edge to whichever of floor/ceil keeps the aspect ratio closest.
struct Size { int w, h; };
inline Size thumb_size(int w, int h, int box) {
  const double aspect = static_cast<double>(w) / h;
  if (aspect >= 1.0) {
    const double y = box / aspect;
    const int lo = std::max(1, static_cast<int>(std::floor(y))), hi = std::max(1, static_cast<int>(std::ceil(y)));
    const int pick = std::abs(aspect - static_cast<double>(box) / lo) <= std::abs(aspect - static_cast<double>(box) / hi) ? lo : hi;
    return {box, pick};
  }
  const double x = box * aspect;
  const int lo = std::max(1, static_cast<int>(std::floor(x))), hi = std::max(1, static_cast<int>(std::ceil(x)));
  const int pick = std::abs(aspect - static_cast<double>(lo) / box) <= std::abs(aspect - static_cast<double>(hi) / box) ? lo : hi;
  return {pick, box};
}

// PROGRESS_OUT, when set, gets "items done <tab> seconds" rows for the video's race chart.
class Progress {
 public:
  Progress() : start_(std::chrono::steady_clock::now()) {
    if (const char* p = std::getenv("PROGRESS_OUT")) f_ = std::fopen(p, "w");
  }
  ~Progress() { if (f_) std::fclose(f_); }
  void tick(long done) {
    if (f_) std::fprintf(f_, "%ld\t%.6f\n", done, seconds());
  }
  double seconds() const {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - start_).count();
  }
 private:
  std::chrono::steady_clock::time_point start_;
  std::FILE* f_ = nullptr;
};

}  // namespace bench
