    "--no-merges"
        commit = ir.Commit(self._hash, self._changes)
            # Set the hash.
            commit_builder.set_hash(line[len(STR_COMMIT) :])