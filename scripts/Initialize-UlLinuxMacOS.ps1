<#.SYNOPSIS
Initialize Linux machine.#>
if ($IsLinux) {
    sudo apt update
    # ! https://askubuntu.com/questions/900285/libegl-so-1-is-not-a-symbolic-link
    # ! https://askubuntu.com/a/1460390
    # ! https://github.com/mccdaq/uldaq
    sudo apt install 'libegl1-mesa-dev' 'libxkbcommon0' 'libxcb-cursor0' 'libxcb-xinerama0' 'libqt5x11extras5' 'gcc' 'g++' 'make' 'bzip2' 'gzip' 'libusb-1.0-0-dev'
}
curl -L -O 'https://github.com/mccdaq/uldaq/releases/download/v1.2.1/libuldaq-1.2.1.tar.bz2'
$Archive = 'libuldaq-1.2.1.tar.bz2'
tar -xvjf $Archive
Remove-Item $Archive
$Source = 'libuldaq-1.2.1'
Push-Location $Source
./configure && make
sudo make install
Pop-Location
Remove-Item -Recurse -Force $Source
