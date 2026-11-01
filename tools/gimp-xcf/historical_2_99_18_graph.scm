; Disclosed bootstrap-seed -> independent stock GIMP2.99.18 writer/readback.
; Generate intermediate seeds with historical_2_99_18_graph_seed.py first.
; In an isolated GIMP3_DIRECTORY, ordinary plug-in-script-fu-eval:
; (begin (load "tools/gimp-xcf/historical_2_99_18_graph.scm")
;   (historical-2-99-18-graphs "WORK_DIRECTORY" "gimp"))
; These are NOT UI-authored files. No devgate, internal setter or graph evaluator.

(define (historical-2-99-18-graph-one work-root output-root name)
  (let* ((seed (string-append work-root "/" name "-seed.xcf"))
         (basename (string-append "historical-2-99-18-graph-" name))
         (saved (string-append output-root "/" basename ".xcf"))
         (png (string-append output-root "/" basename ".png"))
         (image (car (gimp-file-load RUN-NONINTERACTIVE seed)))
         (layers (gimp-image-get-layers image))
         (owner (vector-ref (cadr layers) 0)))
    (gimp-xcf-save RUN-NONINTERACTIVE image 1 (vector owner) saved)
    (gimp-image-delete image)
    (let* ((reopened (car (gimp-file-load RUN-NONINTERACTIVE saved)))
           (reopened-layers (gimp-image-get-layers reopened))
           (reopened-owner (vector-ref (cadr reopened-layers) 0)))
      ; Materialize only this reopened preview copy, never the saved XCF.
      (gimp-drawable-merge-filters reopened-owner)
      (file-png-save RUN-NONINTERACTIVE reopened 1 (vector reopened-owner) png
        FALSE 9 FALSE FALSE FALSE FALSE TRUE FALSE)
      (gimp-message (string-append "stock graph saved/reopened/exported " name))
      (gimp-image-delete reopened))))

(define (historical-2-99-18-graphs work-root output-root)
  (historical-2-99-18-graph-one work-root output-root "invert-linear")
  (historical-2-99-18-graph-one work-root output-root "original-over-inverted"))
