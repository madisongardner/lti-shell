FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Core utilities
        coreutils \
        util-linux \
        findutils \
        diffutils \
        moreutils \
        procps \
        psmisc \
        file \
        which \
        tree \
        less \
        nano \
        vim \
        bash-completion \
        sudo \

        # Text processing
        grep \
        sed \
        gawk \
        jq \

        # File handling
        tar \
        gzip \
        bzip2 \
        xz-utils \
        zip \
        unzip \

        # Dev tools
        build-essential \
        make \
        gcc \
        git \

        # Networking/debugging
        curl \
        wget \
        iproute2 \
        iputils-ping \
        net-tools \
        dnsutils \
        telnet \
        traceroute \

        # Monitoring/debugging
        htop \
        strace \
        ltrace \
        time \

        # Search tools (modern)
        ripgrep \
        fd-find \

        # Misc useful
        rsync \
        screen \
        tmux \
    && groupadd -g 65532 sandbox \
    && useradd -m -u 65532 -g 65532 -s /bin/bash sandbox \
    && cat >> /home/sandbox/.bashrc <<'EOF'

# LTI-Shell defaults
export HISTFILE=/workspace/.bash_history
export HISTSIZE=5000
export HISTFILESIZE=10000
shopt -s histappend
if [ -n "${PROMPT_COMMAND:-}" ]; then
  PROMPT_COMMAND="history -a; ${PROMPT_COMMAND}"
else
  PROMPT_COMMAND="history -a"
fi
EOF

RUN chown sandbox:sandbox /home/sandbox/.bashrc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
USER sandbox

# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#         bash \
#         bash-completion \
#         ca-certificates \
#         coreutils \
#         curl \
#         fd-find \
#         file \
#         findutils \
#         gawk \
#         git \
#         grep \
#         gzip \
#         htop \
#         jq \
#         less \
#         make \
#         nano \
#         procps \
#         psmisc \
#         ripgrep \
#         sed \
#         tar \
#         tree \
#         unzip \
#         vim \
#         wget \
#         which \
#         xz-utils \
#         zip \

# fi
# alias ll='ls -alF'
# alias la='ls -A'
# alias l='ls -CF'
# alias fd='fdfind'