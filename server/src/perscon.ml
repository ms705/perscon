(*pp camlp4o -I `ocamlfind query lwt.syntax` pa_lwt.cmo *)

open Printf
open Arg
open Lwt
open Log
open Cohttp

module Dirs = struct
  exception Unable_to_make_dirs of string * string
  let make dir =
    let rec fn dir accum = 
      match dir with
      |"/"|""|"." -> raise (Unable_to_make_dirs (dir, String.concat "/" accum))
      |_ when try Sys.is_directory dir with Sys_error _ -> false ->
        ignore(List.fold_left (fun a b ->
          let c = Filename.concat a b in
          Unix.handle_unix_error Unix.mkdir c 0o755;
          c) dir accum)
      |_ ->
        fn (Filename.dirname dir) ((Filename.basename dir) :: accum)
    in fn dir []
end

let _ =
  let config_file = ref "perscon.conf" in
  let spec = [
      "-c", Arg.Set_string config_file, "Name of configuration file to use";
  ] in
  parse spec (fun _ -> ()) "";

  logmod "Server" "reading config from %s" !config_file;
  Config.init !config_file;

  Lwt_main.run ( 
    (* obtain the master passphrase *)
    logmod "Server" "obtaining root passphrase";
    let user = Config.User.root () in
    lwt p = Platform.get_pass ~user in
    let phrase = match p with
      |None ->
        prerr_endline "Unable to retrieve passphrase for root user";
        exit 1;
      |Some p -> p in

    let http_port = Config.Dir.port () in
    let http_spec = {  Http_daemon.default_spec with
      Http_daemon.auth = Some ("Personal Container", `Basic ("root", phrase));
      callback = Dispatch.t;
      port = http_port } in
  
    let pop3_port = 1433 in
    let pop3_spec = {  Pop3_daemon.address = "localhost";
       port = pop3_port; timeout = Some 20; cb=Pop3_daemon.cb } in

    logmod "Server" "creating log and db directories";
    List.iter Dirs.make [ Config.Dir.db () ; Config.Dir.log (); Config.Dir.att () ];

    logmod "Server" "initializing MIME types";
    Magic_mime.init (Filename.concat (Config.Dir.etc ()) "mime.types") >>

    let http =
      logmod "Server" "listening to HTTP on port %d" http_port;
      Http_daemon.main http_spec in
    let pop3 = 
      logmod "Server" "listening to POP3 on port %d" pop3_port;
      Pop3_daemon.main pop3_spec in

    join [ http; pop3 ]

  )
