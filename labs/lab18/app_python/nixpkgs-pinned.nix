# Pinned nixpkgs (nixos-24.11 @ 50ab793786d9de88ee30ec4e4c24fb4236fc2674) for reproducible Lab 18 builds without relying on host <nixpkgs>.
import (builtins.fetchTarball {
  url = "https://github.com/NixOS/nixpkgs/archive/50ab793786d9de88ee30ec4e4c24fb4236fc2674.tar.gz";
  # Fixed-output hash verified with `nix-build` (must match Nix’s unpack hash, not raw `curl | sha256sum`).
  sha256 = "1s2gr5rcyqvpr58vxdcb095mdhblij9bfzaximrva2243aal3dgx";
}) { }
