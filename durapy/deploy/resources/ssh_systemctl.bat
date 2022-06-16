ssh -p %4 -T %2@%3 "set -x && [ \"$(uname -o)\" = \"Msys\" ] && exit 1 || cd ~/Development/python || cd ~/python || exit 1 && sudo systemctl %1 %5"
