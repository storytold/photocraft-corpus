; Original fixtures authored with stock GIMP 2.99.18, ScriptFu public PDB only.
; Invoke with an isolated GIMP3_DIRECTORY and plug-in-script-fu-eval:
; (begin (load "tools/gimp-xcf/historical_2_99_18.scm")
;   (historical-2-99-18-generate "gimp" "historical-source-facts.scm"))
; Paths may be absolute at invocation; no invocation paths enter fixture metadata.
; Fonts are referenced by name only and are not distributed.

(define (historical-2-99-18-one output-root basename precision port)
  (let* ((xcf (string-append output-root "/" basename ".xcf"))
         (png (string-append output-root "/" basename ".png"))
         (image (car (gimp-image-new-with-precision 64 32 RGB precision)))
         (font (car (gimp-context-get-font)))
         (text (car (gimp-text-layer-new image "Historical XCF" font 12 PIXELS)))
         (vectors (car (gimp-vectors-new image "Original historical Bezier"))))
    (gimp-image-insert-layer image text 0 0)
    (gimp-layer-set-offsets text 0 0)
    (gimp-text-layer-set-color text '(0 0 0))
    (gimp-image-insert-vectors image vectors 0 0)
    (gimp-vectors-stroke-new-from-points vectors 0 12
      #(2.0 4.0 4.0 4.0 8.0 2.0 40.0 24.0 44.0 24.0 48.0 28.0) TRUE)
    (gimp-image-set-metadata image "")
    (gimp-xcf-save RUN-NONINTERACTIVE image 1 (vector text) xcf)
    (gimp-image-delete image)
    (let* ((loaded (car (gimp-file-load RUN-NONINTERACTIVE xcf)))
           (layers (gimp-image-get-layers loaded))
           (paths (gimp-image-get-vectors loaded))
           (loaded-text (vector-ref (cadr layers) 0))
           (loaded-path (vector-ref (cadr paths) 0))
           (strokes (gimp-vectors-get-strokes loaded-path))
           (stroke-id (vector-ref (cadr strokes) 0)))
      (write (list basename
        (gimp-image-get-precision loaded)
        (gimp-text-layer-get-text loaded-text)
        (gimp-resource-get-name (car (gimp-text-layer-get-font loaded-text)))
        (gimp-text-layer-get-color loaded-text)
        (gimp-drawable-get-offsets loaded-text)
        (gimp-vectors-stroke-get-points loaded-path stroke-id)) port)
      (newline port)
      (gimp-image-set-metadata loaded "")
      ; PNG is the document canvas, not the larger editable text-layer extent.
      ; Only this reopened in-memory preview copy is resized; XCF stays intact.
      (gimp-layer-resize-to-image-size loaded-text)
      (file-png-save RUN-NONINTERACTIVE loaded 1 (vector loaded-text) png
        FALSE 9 FALSE FALSE FALSE FALSE TRUE FALSE)
      (gimp-message (string-append "historical saved/reopened/exported " basename))
      (gimp-image-delete loaded))))

(define (historical-2-99-18-generate output-root facts-path)
  (call-with-output-file facts-path
    (lambda (port)
      (write (list 'gimp-version (gimp-version)) port)
      (newline port)
      (historical-2-99-18-one output-root
        "historical-2-99-18-text-path-u8" 150 port)
      (historical-2-99-18-one output-root
        "historical-2-99-18-text-path-float" 600 port))))
