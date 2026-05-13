{ pkgs ? import ./nixpkgs-pinned.nix,
  app ? import ./default.nix { inherit pkgs; }
}:

pkgs.dockerTools.buildLayeredImage {
  name = "haruyume/devops-info-service-nix";
  tag = "1.0.0-lab18";

  contents = [
    app
    pkgs.bash
    pkgs.coreutils
    pkgs.cacert
  ];

  config = {
    Cmd = [ "${app}/bin/devops-info-service" ];
    WorkingDir = "/";
    ExposedPorts = { "5000/tcp" = { }; };
    Env = [
      "PYTHONUNBUFFERED=1"
      "SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
    ];
  };

  created = "1970-01-01T00:00:01Z";
}
