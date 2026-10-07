"""Local reference-editing presets. No extra model downloads are required."""
ANIME_PROMPT = 'Redraw this entire image as a Japanese anime film frame. Use crisp ink outlines, simple flat color fills and two-tone cel shading, with a hand-drawn 2D animation aesthetic. Preserve the same recognizable person, original skin color, age, face proportions, natural eye size, hair, expression, clothing, hand positions and exact room composition and framing. Change only the drawing style.'
PRESERVE = (' Preserve the source camera angle, framing, room layout, positions of objects, '
            'the person\'s identity, hairstyle, glasses if present, expression, body pose and hand gestures. '
            'Apply the requested visual language consistently to the entire scene. Do not add text or a watermark.')

STYLES = {
    'anime': ('Anime film', ANIME_PROMPT, 'Ink outlines, flat colors and two-tone cel shading.'),
    'doodle': ('Black ink doodle',
        'Turn the full camera image into a playful hand-drawn doodle in pure black ink on a clean white paper background. '
        'Use loose irregular pen outlines, sparse scribbled hatching, simple cartoon shapes and expressive linework. '
        'Use only black ink and white paper: no color, gray washes, photorealistic shading or filled photographic textures.' + PRESERVE,
        'Loose black pen strokes on white paper. Best at 100% style strength.'),
    'painted_3d': ('Painted 3D animation',
        'Recreate this scene as a cinematic stylized 3D animated series frame combining hand-painted textures with '
        'slightly low-poly faceted geometry, exaggerated boxy character proportions, angular cheekbones and chunky sculpted hair. '
        'Use visible painterly brush marks, graphic shadow shapes, dramatic colored rim lighting, rich art-directed colors '
        'and occasional expressive 2D ink accents over the 3D rendering. Keep the character recognizable. '
        'Avoid smooth glossy plastic, a generic soft cartoon look, photorealism and conventional flat anime.' + PRESERVE,
        'Boxy low-poly forms, painted textures and graphic cinematic lighting.'),
    'xray': ('X-ray skull',
        'Create a fictional artistic X-ray vision rendering of this camera scene. Render the person\'s head as a clearly '
        'visible three-dimensional human skull, with ivory bone, readable eye sockets, cheekbones, jaw and individual teeth, '
        'in the same head orientation as the source. Use a faint translucent blue silhouette around the skull and subtly '
        'visible neck and hand bones. Use cool cyan rim lighting and a dark subdued version of the original room. '
        'Make the skull sculptural and non-graphic, with no blood, injury or exposed tissue. '
        'This is an imagined stylized anatomy illustration, not a medical scan. Preserve the camera framing, head pose, '
        'body pose, hand gestures and arrangement of the scene. Do not add labels or a watermark.',
        'Fictional 3D skull effect; the camera cannot see real bones.'),
    'paper': ('Layered paper cutout',
        'Rebuild this entire scene as handcrafted layered colored paper art. Form the person and room from crisp '
        'cut-paper silhouettes, overlapping matte paper layers, subtle paper fibers, bevel-free edges and gentle '
        'cast shadows between layers. Use a warm restrained palette, simple shapes and a tactile shallow diorama look. '
        'Avoid ink drawing, glossy 3D materials and photorealism.' + PRESERVE,
        'Colored paper layers with tactile fibers and soft cast shadows.'),
    'clay': ('Clay stop-motion',
        'Transform the camera scene into a charming handmade clay stop-motion set. Sculpt the recognizable person '
        'and room from matte colored modeling clay with tiny fingerprints, imperfect seams, chunky rounded shapes '
        'and miniature practical props. Use warm studio lighting and a tactile miniature-set aesthetic. '
        'Keep the exact source pose and silhouette; do not invent raised hands, a wave or a peace sign. '
        'If the camera image does not show hands, keep all hands outside the frame. '
        'Avoid glossy plastic, polished computer animation, paper layers and ink outlines.' + PRESERVE,
        'Handmade clay characters, fingerprints and miniature-set lighting.'),
    'glass': ('Stained glass mosaic',
        'Translate the whole scene into an intricate stained-glass window mosaic. Build recognizable face, hair, '
        'clothes and room objects from luminous jewel-colored glass pieces separated by dark lead outlines. '
        'Use translucent textured glass, geometric faceted segmentation and light glowing through every pane. '
        'Keep the figure readable rather than turning the image into an abstract pattern.' + PRESERVE,
        'Luminous jewel-colored glass pieces divided by dark lead lines.'),
    'blueprint': ('Cyanotype blueprint',
        'Redraw the camera scene as a precise white-line technical blueprint printed on deep Prussian blue cyanotype paper. '
        'Show the recognizable person, hands, clothes and room as clean contour lines, sparse construction curves, '
        'cross-sectional hatch lines and fine wireframe detail. Keep the navy blue ground uniform and all linework white or '
        'very pale cyan. No readable labels, measurements, logos, photographic fills or other colors.' + PRESERVE,
        'White technical contours and wireframes on deep blue paper.'),
    'pixel': ('Retro pixel art',
        'Recreate the scene as carefully authored retro 16-bit pixel art with a consistent visible square-pixel grid, '
        'crisp stepped edges, a limited coordinated color palette, clustered pixel shading and selective dithering. '
        'Keep recognizable facial features, hair, glasses, clothing and room objects. Avoid smoothing, blur, '
        'vector outlines, glossy 3D rendering and merely pixelating the original photograph.' + PRESERVE,
        'Crisp 16-bit pixel clusters, limited colors and selective dithering.'),
}
STYLE_LABELS = {value[0]: key for key, value in STYLES.items()}
STYLE_LABELS['Custom instruction'] = 'custom'


def infer_style(prompt):
    return next((key for key, value in STYLES.items() if value[1] == prompt), 'custom')


def style_name(key):
    return STYLES[key][0] if key in STYLES else 'Custom instruction'
