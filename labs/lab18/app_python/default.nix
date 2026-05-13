{ pkgs ? import ./nixpkgs-pinned.nix }:
let
  inherit (pkgs) stdenvNoCC makeWrapper python3 lib;
  py = python3.withPackages (ps: with ps; [
    flask
    python-json-logger
    prometheus-client
  ]);
in
stdenvNoCC.mkDerivation {
  pname = "devops-info-service";
  version = "1.0.0";
  src = lib.cleanSourceWith {
    src = ./.;
    filter = path: type:
      let b = baseNameOf path; in
      lib.elem b [
        "app.py"
        "requirements.txt"
        "default.nix"
        "docker.nix"
        "flake.nix"
        "flake.lock"
        "nixpkgs-pinned.nix"
        "requirements-unpinned.txt"
      ];
  };

  nativeBuildInputs = [ makeWrapper ];

  # Pure copy + wrapper: no network at install time; deps come from py closure.
  installPhase = ''
    mkdir -p $out/share/devops-info-service
    cp app.py $out/share/devops-info-service/app.py

    makeWrapper ${py}/bin/python3 $out/bin/devops-info-service \
      --add-flags "$out/share/devops-info-service/app.py" \
      --prefix PATH : "${py}/bin"
  '';

  meta = with pkgs.lib; {
    description = "DevOps Info Service (Flask) — Lab 18 Nix build";
    mainProgram = "devops-info-service";
    license = licenses.mit;
  };
}
