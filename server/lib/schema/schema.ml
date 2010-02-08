module Config = struct
  type c = {
    db_directory: string;
    att_directory: string;
    log_directory: string;
    static_directory: string;
    etc_directory: string;
    port: int
  } with json
end
 
module Entry = struct
  type 
    contact = {
      c_origin: string;
      mutable c_mtime: float;
      c_uid: string;
      mutable c_meta: (string * string) list;
      mutable c_atts: att list
   }
 and
   svc = {
     s_ty: string;
     s_id: string;
     mutable s_co: string
   }
 and
   att = {
     a_uid: string;
     mutable a_mime: string
   }
 and
   e = {
     e_origin: string;
     e_mtime: float;
     e_uid: string;
     mutable e_from: svc list;
     mutable e_to: svc list;
     mutable e_meta: (string * string) list;
     mutable e_folder: string;
     mutable e_tags: string list;
     mutable e_atts: att list;
   }
 with 
   json, 
   orm ( debug: leak;
         dot: "schema.dot"; 
         unique: contact<c_uid>, e<e_uid>, svc<s_ty,s_id>, att<a_uid>;
         index: e<e_origin,e_folder>  )

 type e_query = <
     results: int;
     rows: e list
 > with json

end
