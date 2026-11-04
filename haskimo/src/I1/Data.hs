{-# LANGUAGE TemplateHaskell #-}
-- | Data.hs -- the system files of the language, embedded at build time.
module I1.Data (libFiles, doc1Text, doc2Text) where

import I1.EmbedTH

-- | the prelude files (lib/*.imo), in loading order, as (path, text)
libFiles :: [(FilePath, String)]
libFiles = $(embedLib)

doc1Text :: String
doc1Text = $(embedText "docs/doc1.sbl")

doc2Text :: String
doc2Text = $(embedText "docs/doc2.sbl")
