// Prints OpenCV's build information (which libjpeg-turbo and libwebp it carries) for the session's meta.json.
#include <iostream>

#include <opencv2/core.hpp>

int main() {
  std::cout << cv::getBuildInformation();
  return 0;
}
