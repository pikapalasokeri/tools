#include <iostream>
#include <string>

int main()
{
  std::string lines[2];
  int currentLineIx = 0;
  bool isFirstLine = true;
  while (std::getline(std::cin, lines[currentLineIx]))
  {
    currentLineIx = !currentLineIx;
    if (isFirstLine)
    {
      isFirstLine = false;
    }
    else
    {
      std::cout << lines[currentLineIx] << std::endl;
    }
  }
  std::cout << lines[!currentLineIx];

  return 0;
}
