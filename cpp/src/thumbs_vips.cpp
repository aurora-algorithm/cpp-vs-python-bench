// Test 2, libvips from C++: the same thumbnails through vips_thumbnail, the call pyvips makes.
// usage: thumbs_vips IN_DIR OUT_DIR
#include <iostream>
#include <string>

#include <vips/vips.h>

#include "common.hpp"

constexpr int SIZE = 512;
constexpr int QUALITY = 80;

int main(int argc, char** argv) {
  if (argc != 3) { std::cerr << "usage: thumbs_vips IN_DIR OUT_DIR\n"; return 2; }
  if (VIPS_INIT(argv[0])) { std::cerr << vips_error_buffer() << "\n"; return 1; }
  const bench::fs::path dst = argv[2];
  bench::fs::create_directories(dst);
  bench::Progress progress;
  long done = 0;
  for (const auto& path : bench::photos(argv[1])) {
    VipsImage* thumb = nullptr;
    if (vips_thumbnail(path.string().c_str(), &thumb, SIZE, nullptr)) { std::cerr << vips_error_buffer() << "\n"; return 1; }
    const std::string out = (dst / (path.stem().string() + ".webp")).string();
    const int rc = vips_webpsave(thumb, out.c_str(), "Q", QUALITY, nullptr);
    g_object_unref(thumb);
    if (rc) { std::cerr << vips_error_buffer() << "\n"; return 1; }
    progress.tick(++done);
  }
  vips_shutdown();
  return 0;
}
