// Test 1: shrink a photo 4x by hand. Every output pixel is the average of a 4 x 4 block, one channel at a time.
// usage: shrink_loop IN.ppm OUT.ppm
#include <cstdio>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

#include "common.hpp"

constexpr int BLOCK = 4;

int main(int argc, char** argv) {
  if (argc != 3) { std::cerr << "usage: shrink_loop IN.ppm OUT.ppm\n"; return 2; }
  std::ifstream in(argv[1], std::ios::binary);
  std::string magic;
  int width = 0, height = 0, maxval = 0;
  in >> magic >> width >> height >> maxval;
  in.get();
  if (magic != "P6" || maxval != 255) { std::cerr << argv[1] << ": not an 8-bit P6 PPM\n"; return 1; }
  std::vector<unsigned char> src(static_cast<size_t>(width) * height * 3);
  in.read(reinterpret_cast<char*>(src.data()), static_cast<std::streamsize>(src.size()));
  const int out_w = width / BLOCK, out_h = height / BLOCK;
  std::vector<unsigned char> out(static_cast<size_t>(out_w) * out_h * 3);
  bench::Progress progress;
  for (int y = 0; y < out_h; y++) {
    for (int x = 0; x < out_w; x++) {
      for (int c = 0; c < 3; c++) {
        int total = 0;
        for (int dy = 0; dy < BLOCK; dy++) {
          const size_t row = (size_t(y * BLOCK + dy) * width + x * BLOCK) * 3 + c;
          for (int dx = 0; dx < BLOCK; dx++) {
            total += src[row + dx * 3];
          }
        }
        out[(static_cast<size_t>(y) * out_w + x) * 3 + c] = static_cast<unsigned char>((total + 8) / 16);
      }
    }
    if (y % 8 == 7 || y == out_h - 1) progress.tick(y + 1);
  }
  std::ofstream f(argv[2], std::ios::binary);
  f << "P6\n" << out_w << " " << out_h << "\n255\n";
  f.write(reinterpret_cast<const char*>(out.data()), static_cast<std::streamsize>(out.size()));
  return 0;
}
