{
  description = "HTTPing - HTTP response time measurement tool";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python311;
        pythonPackages = python.pkgs;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pythonPackages; [
            python
            requests
            dnspython
          ];
          
          shellHook = ''
            echo "HTTPing development environment loaded"
            echo "Python version: $(python --version)"
            echo "Available commands:"
            echo "  python httping.py --help"
            echo "  python httping.py https://example.com"
            echo "  python httping.py https://example.com -i 2.5 -H 'server,content-type'"
          '';
        };

        packages.default = pkgs.stdenv.mkDerivation {
          name = "httping";
          version = "1.0.0";
          
          src = ./.;
          
          buildInputs = with pythonPackages; [
            (python.withPackages (ps: [ ps.requests ps.dnspython ]))
          ];
          
          installPhase = ''
            mkdir -p $out/bin
            cp httping.py $out/bin/httping
            chmod +x $out/bin/httping
          '';
          
          meta = with pkgs.lib; {
            description = "HTTP response time measurement tool";
            homepage = "https://github.com/cransom/httping";
            license = licenses.mit;
            maintainers = [ ];
            platforms = platforms.all;
          };
        };
      });
}
