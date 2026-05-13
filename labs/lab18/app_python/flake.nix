{
  description = "Lab 18 — reproducible DevOps Info Service (Nix flake + dockerTools)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        devops-info-service = import ./default.nix { inherit pkgs; };
        dockerImage = import ./docker.nix { inherit pkgs; };
        pyDev = pkgs.python3.withPackages (ps: with ps; [
          flask
          python-json-logger
          prometheus-client
        ]);
      in
      {
        packages = {
          default = devops-info-service;
          dockerImage = dockerImage;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pyDev
            pkgs.python3
          ];
          shellHook = ''
            echo "Lab 18 dev shell — $(python3 --version)"
          '';
        };
      });
}
