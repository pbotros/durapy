#!/bin/bash
# Usage: [$0] <username> <hostname> <port> <mubmi_appname>

ssh -p ${3} -T ${1}@${2} 'set -x && cd ~/Development/python || cd ~/python || exit 1 && echo $(git branch | grep \* | cut -d \  -f2) && git pull && [ \"$(uname -o)\" = "Msys" ] && exit 0 || sudo systemctl daemon-reload && sudo systemctl restart '${4}
ret=$?
echo "Return code ${ret}"
exit $ret
