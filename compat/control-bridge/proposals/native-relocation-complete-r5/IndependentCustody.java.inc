    static final class Quarantined {
        static void validate(JsonObject p,String tx,String capsule){
            if(!p.get("transaction_id").getAsString().equals(tx)||!p.get("capsule_id").getAsString().equals(capsule)||!p.get("operation").getAsString().equals("move")
                ||!p.get("clone_invoked").getAsBoolean()||!p.get("intent_written").getAsBoolean()||!p.get("failed").getAsBoolean()||!p.get("quarantine").getAsBoolean()
                ||!p.get("cleanup_passed").getAsBoolean()||p.get("owned_chunk_tickets").getAsInt()!=0||p.get("pending_owned_futures").getAsInt()!=0||p.get("pending_shared_chunk_futures").getAsInt()!=0
                ||p.has("ticket_cleanup_error")||p.has("lease_cleanup_error"))throw new IllegalStateException("Exact genuinely invoked failed clean native move required");
        }
    }
    private void marked(JsonObject reference)throws Exception{
        Path p=owned(reference.get("path").getAsString());
        if(!new String(bytes(p.resolveSibling(p.getFileName()+".complete"),128),StandardCharsets.UTF_8).trim().equals(reference.get("sha256").getAsString()))throw new IllegalStateException("Exact immutable native terminal marker required");
    }
    private void recordConserved(MinecraftServer server)throws Exception{
        JsonObject intent=auditQuarantined(server,false),audit=ref("native_custody_audit",1048576),review=ref("custody_resolution_review",65536);marked(request.getAsJsonObject("native_custody_audit"));
        if(!audit.get("operation").getAsString().equals("inspect-quarantined")||!audit.get("transaction_id").equals(JSON.toJsonTree(report.get("transaction_id")))
            ||!audit.get("native_runtime_id").getAsString().equals(runtimeId)||!audit.get("pack_sha256").equals(request.get("pack_sha256"))||!audit.get("current_backup_sha256").equals(request.get("backup_sha256"))
            ||!audit.get("cleanup_passed").getAsBoolean()||!audit.get("source_AIR_passed").getAsBoolean()||!audit.get("native_content_conservation_passed").getAsBoolean()
            ||!audit.getAsJsonArray("destination_state_differences").isEmpty()||!audit.getAsJsonArray("destination_survival_failures").isEmpty()
            ||audit.get("owned_chunk_tickets").getAsInt()!=0||audit.get("pending_owned_futures").getAsInt()!=0||audit.get("pending_shared_chunk_futures").getAsInt()!=0
            ||audit.has("ticket_cleanup_error")||audit.has("lease_cleanup_error"))throw new IllegalStateException("Actual fresh independent native custody audit must pass; failed move is never relabelled");
        Instant at=Instant.parse(audit.get("finished").getAsString()),created=Instant.parse(review.get("created").getAsString());
        if(at.isAfter(Instant.now())||at.isBefore(Instant.now().minusSeconds(120))||created.isAfter(Instant.now())||created.isBefore(at))throw new IllegalStateException("Fresh actual audit and later explicit review required");
        if(!review.get("format").getAsString().equals("awft-explicit-independent-custody-review:1")||!review.get("approved").getAsBoolean()||!review.get("allow_record_current_custody_only").getAsBoolean()
            ||!review.get("transaction_id").equals(audit.get("transaction_id"))||!review.get("failed_move_terminal_sha256").equals(request.getAsJsonObject("quarantined_move_terminal").get("sha256"))
            ||!review.get("native_audit_sha256").equals(request.getAsJsonObject("native_custody_audit").get("sha256")))throw new IllegalStateException("Separate explicit Root-reviewed custody authority required");
        if(!Boolean.TRUE.equals(report.get("source_AIR_passed"))||!Boolean.TRUE.equals(report.get("native_content_conservation_passed"))
            ||!((JsonArray)report.get("destination_state_differences")).isEmpty()||!((JsonArray)report.get("destination_survival_failures")).isEmpty()
            ||!audit.getAsJsonArray("current_native_snapshots").equals(report.get("current_native_snapshots")))throw new IllegalStateException("Current exact native custody changed after real audit");
        ready(server);JsonObject record=new JsonObject();record.addProperty("format","awft-native-independent-custody-resolution:1");record.addProperty("transaction_id",report.get("transaction_id").toString());
        record.addProperty("capsule_id",capsuleId);record.addProperty("created",Instant.now().toString());record.addProperty("active_intent_file",activeIntent(intent));record.addProperty("intent_sha256",report.get("original_intent_sha256").toString());
        record.addProperty("original_quarantine_sha256",report.get("original_quarantine_sha256").toString());record.add("failed_native_move",request.get("quarantined_move_terminal").deepCopy());
        record.add("native_custody_audit",request.get("native_custody_audit").deepCopy());record.add("explicit_review",request.get("custody_resolution_review").deepCopy());
        record.add("before_native_snapshots",intent.get("before_native_snapshots").deepCopy());record.add("current_native_snapshots",((JsonArray)report.get("current_native_snapshots")).deepCopy());
        record.addProperty("native_process_pid",ProcessHandle.current().pid());record.addProperty("native_process_started_at",ProcessHandle.current().info().startInstant().orElseThrow().toString());
        record.addProperty("source_AIR_passed",true);record.addProperty("current_destination_full_states_and_survival_passed",true);record.addProperty("native_content_conservation_passed",true);
        record.addProperty("original_move_passed",false);record.addProperty("clone_or_retry_invoked",false);Path path=ledger.resolve("conserved-after-independent-repair.json");durable(path,record);
        Ledger.create(path.resolveSibling(path.getFileName()+".sha256"),(sha(bytes(path,1048576))+"\n").getBytes(StandardCharsets.UTF_8));
        report.put("independent_custody_resolution_written",true);report.put("original_move_passed",false);finish("recorded independently proven current custody; original failed move/quarantine retained; no retry",false);
    }
    private JsonObject completedCustody(Path directory,String key)throws Exception{
        Path file=Files.exists(directory.resolve("completed.json"),LinkOption.NOFOLLOW_LINKS)?directory.resolve("completed.json"):directory.resolve("conserved-after-independent-repair.json");
        byte[] raw=bytes(file,1048576);if(!new String(bytes(file.resolveSibling(file.getFileName()+".sha256"),128),StandardCharsets.UTF_8).trim().equals(sha(raw)))throw new IllegalStateException("Durable native custody marker differs");
        JsonObject done=JsonParser.parseString(new String(raw,StandardCharsets.UTF_8)).getAsJsonObject();
        if(!done.get("transaction_id").getAsString().equals(key)||!done.get("intent_sha256").getAsString().equals(sha(bytes(directory.resolve(activeIntent(done)),1048576))))throw new IllegalStateException("Foreign actual custody/intent");
        if(file.getFileName().toString().startsWith("conserved-")){
            if(!done.get("format").getAsString().equals("awft-native-independent-custody-resolution:1")||done.get("original_move_passed").getAsBoolean()||done.get("clone_or_retry_invoked").getAsBoolean()
                ||!done.get("source_AIR_passed").getAsBoolean()||!done.get("current_destination_full_states_and_survival_passed").getAsBoolean()||!done.get("native_content_conservation_passed").getAsBoolean())throw new IllegalStateException("Independent custody is not a replay/completion substitute");
            JsonObject audit=exactRef(done.getAsJsonObject("native_custody_audit"),1048576);marked(done.getAsJsonObject("native_custody_audit"));
            JsonObject failed=exactRef(done.getAsJsonObject("failed_native_move"),1048576);marked(done.getAsJsonObject("failed_native_move"));Quarantined.validate(failed,key,done.get("capsule_id").getAsString());
            JsonObject review=exactRef(done.getAsJsonObject("explicit_review"),65536);
            if(!review.get("approved").getAsBoolean()||!review.get("allow_record_current_custody_only").getAsBoolean()||!audit.get("native_content_conservation_passed").getAsBoolean()
                ||!audit.get("source_AIR_passed").getAsBoolean()||!audit.get("cleanup_passed").getAsBoolean())throw new IllegalStateException("Historical independent custody provenance differs");
            String quarantine=activeIntent(done).equals("intent.json")?"quarantine.json":"quarantine-after-uninvoked-resolution.json";
            if(!sha(bytes(directory.resolve(quarantine),1048576)).equals(done.get("original_quarantine_sha256").getAsString()))throw new IllegalStateException("Original invoked quarantine changed");
        }return done;
    }
