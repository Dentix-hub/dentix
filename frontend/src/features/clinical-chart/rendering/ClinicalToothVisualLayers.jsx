import { memo } from 'react';
import {
    VISUAL_LAYER_ROLES,
    VISUAL_LAYER_SEQUENCE,
} from '../domain/visualRuleRegistry';
import { getSurfaceGeometry } from './surfaceGeometry';

const getLayerIndex = (layerRole) => VISUAL_LAYER_SEQUENCE.indexOf(layerRole);

const getLayerInstructions = (toothVisual, layerRole) => (
    toothVisual?.byLayer?.[layerRole] ?? []
);

const getSurfacePath = (toothKey, surfaceCode) => (
    getSurfaceGeometry(toothKey)?.surfaces.find((surface) => (
        surface.surfaceCode === surfaceCode
    ))?.path ?? null
);

const InstructionGroup = ({ instruction, children }) => (
    <g
        data-code={instruction.code}
        data-effect={instruction.effect}
        data-phase={instruction.phase ?? undefined}
        data-target-kind={instruction.target.kind}
        data-target-root={instruction.target.rootId ?? undefined}
        data-target-surface={instruction.target.surfaceCode ?? undefined}
        pointerEvents="none"
    >
        {children}
    </g>
);

const CrownInstruction = ({ instruction, toothKey, crownPath, crownTransform }) => {
    const { effect, presentation, target } = instruction;
    const surfacePath = target.kind === 'surface'
        ? getSurfacePath(toothKey, target.surfaceCode)
        : null;

    if (effect === 'present') return null;

    if (effect === 'missing') {
        return (
            <InstructionGroup instruction={instruction}>
                <path
                    d={crownPath}
                    transform={crownTransform}
                    fill="none"
                    stroke={presentation.stroke}
                    strokeDasharray={presentation.strokeDasharray}
                    strokeWidth={presentation.strokeWidth}
                />
                <path d="M16,17 L34,39 M34,17 L16,39" fill="none" stroke={presentation.stroke} strokeWidth="1.7" />
            </InstructionGroup>
        );
    }

    if (effect === 'extracted') {
        return (
            <InstructionGroup instruction={instruction}>
                <path d="M13,13 L37,43 M37,13 L13,43" fill="none" stroke={presentation.stroke} strokeLinecap="round" strokeWidth={presentation.strokeWidth} />
            </InstructionGroup>
        );
    }

    if (effect === 'impacted' || effect === 'unerupted') {
        return (
            <InstructionGroup instruction={instruction}>
                <path
                    d={crownPath}
                    transform={crownTransform}
                    fill={presentation.fill}
                    fillOpacity={presentation.fillOpacity}
                    stroke={presentation.stroke}
                    strokeDasharray={presentation.strokeDasharray}
                    strokeWidth={presentation.strokeWidth}
                />
                {effect === 'impacted' ? (
                    <path d="M17,33 Q25,17 33,33 M29,29 L33,33 L28,35" fill="none" stroke={presentation.stroke} strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
                ) : (
                    <path d="M19,21 L25,28 L31,21" fill="none" stroke={presentation.stroke} strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
                )}
            </InstructionGroup>
        );
    }

    if (effect === 'surface-caries') {
        return (
            <InstructionGroup instruction={instruction}>
                {surfacePath ? (
                    <path
                        d={surfacePath}
                        fill={presentation.fill}
                        fillOpacity={presentation.fillOpacity}
                        stroke={presentation.stroke}
                        strokeLinejoin="round"
                        strokeWidth={presentation.strokeWidth}
                    />
                ) : (
                    <path d="M18,20 C21,15 30,16 33,21 C36,27 31,34 24,33 C18,32 14,25 18,20 Z" fill={presentation.fill} fillOpacity={presentation.fillOpacity} stroke={presentation.stroke} strokeWidth={presentation.strokeWidth} />
                )}
            </InstructionGroup>
        );
    }

    if (effect === 'fracture-line') {
        return (
            <InstructionGroup instruction={instruction}>
                <path d="M18,9 L27,19 L22,27 L31,36 L26,47" fill="none" stroke={presentation.stroke} strokeLinecap="round" strokeLinejoin="round" strokeWidth={presentation.strokeWidth} />
            </InstructionGroup>
        );
    }

    if (effect === 'pain-marker') {
        return (
            <InstructionGroup instruction={instruction}>
                <circle cx="39" cy="13" fill={presentation.fill} r="5.5" stroke={presentation.stroke} strokeWidth={presentation.strokeWidth} />
                <path d="M39,10 L39,14 M39,16.5 L39,17" fill="none" stroke="#ffffff" strokeLinecap="round" strokeWidth="1.6" />
            </InstructionGroup>
        );
    }

    if (effect === 'surface-restoration' && surfacePath) {
        return (
            <InstructionGroup instruction={instruction}>
                <path
                    d={surfacePath}
                    fill={presentation.fill}
                    fillOpacity={presentation.fillOpacity}
                    stroke={presentation.stroke}
                    strokeDasharray={presentation.strokeDasharray}
                    strokeLinejoin="round"
                    strokeWidth={presentation.strokeWidth}
                />
                <path d={surfacePath} fill="none" opacity="0.5" stroke="#ffffff" strokeWidth="0.55" />
            </InstructionGroup>
        );
    }

    if (['prosthetic-crown', 'bridge-unit', 'implant-crown'].includes(effect)) {
        return (
            <InstructionGroup instruction={instruction}>
                <path
                    d={crownPath}
                    transform={crownTransform}
                    fill={presentation.fill}
                    fillOpacity={presentation.fillOpacity}
                    stroke={presentation.stroke}
                    strokeDasharray={presentation.strokeDasharray}
                    strokeLinejoin="round"
                    strokeWidth={presentation.strokeWidth}
                />
                {effect === 'bridge-unit' && (
                    <>
                        <path d="M1,13 L49,13" fill="none" stroke={presentation.stroke} strokeWidth="2.2" />
                        <circle cx="3" cy="13" fill={presentation.fill} r="2.5" stroke={presentation.stroke} strokeWidth="1" />
                        <circle cx="47" cy="13" fill={presentation.fill} r="2.5" stroke={presentation.stroke} strokeWidth="1" />
                    </>
                )}
            </InstructionGroup>
        );
    }

    if (effect === 'endodontic-therapy') {
        return (
            <InstructionGroup instruction={instruction}>
                <path d="M19,20 Q25,16 31,20 L29,31 Q25,35 21,31 Z" fill={presentation.fill} fillOpacity={presentation.fillOpacity} stroke={presentation.stroke} strokeDasharray={presentation.strokeDasharray} strokeWidth="1.3" />
            </InstructionGroup>
        );
    }

    if (effect === 'surgical-extraction') {
        return (
            <InstructionGroup instruction={instruction}>
                <path d="M13,13 L37,43 M37,13 L13,43" fill="none" stroke={presentation.stroke} strokeDasharray={presentation.strokeDasharray} strokeLinecap="round" strokeWidth={presentation.strokeWidth} />
            </InstructionGroup>
        );
    }

    if (effect === 'selected') {
        return (
            <InstructionGroup instruction={instruction}>
                <path
                    d={surfacePath ?? crownPath}
                    transform={surfacePath ? undefined : crownTransform}
                    fill={presentation.fill}
                    fillOpacity={presentation.fillOpacity}
                    stroke={presentation.stroke}
                    strokeWidth={presentation.strokeWidth}
                />
            </InstructionGroup>
        );
    }

    if (effect === 'disabled') {
        return (
            <InstructionGroup instruction={instruction}>
                <path
                    d={crownPath}
                    transform={crownTransform}
                    fill="#e2e8f0"
                    fillOpacity="0.28"
                    stroke={presentation.stroke}
                    strokeDasharray="2 2"
                    strokeWidth="1"
                />
            </InstructionGroup>
        );
    }

    return null;
};

const CROWN_LAYER_ROLES = [
    VISUAL_LAYER_ROLES.LIFECYCLE,
    VISUAL_LAYER_ROLES.FINDINGS,
    VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
    VISUAL_LAYER_ROLES.PLANNED_ACTIVE_WORK,
    VISUAL_LAYER_ROLES.SELECTION_FOCUS,
];

export const CrownVisualLayers = memo(function CrownVisualLayers({
    toothKey,
    crownPath,
    crownClipId,
    crownTransform,
    toothVisual,
}) {
    return CROWN_LAYER_ROLES.map((layerRole) => {
        const instructions = getLayerInstructions(toothVisual, layerRole);
        if (instructions.length === 0) return null;
        return (
            <g
                clipPath={`url(#${crownClipId})`}
                data-layer-index={getLayerIndex(layerRole)}
                data-layer-role={layerRole}
                key={layerRole}
            >
                {instructions.map((instruction) => (
                    <CrownInstruction
                        crownPath={crownPath}
                        crownTransform={crownTransform}
                        instruction={instruction}
                        key={instruction.instructionId}
                        toothKey={toothKey}
                    />
                ))}
            </g>
        );
    });
});

const targetMatchesRoot = (target, root) => (
    target.kind === 'tooth' || target.rootId === root.rootId
);

const EndodonticRootInstruction = ({ instruction, roots }) => (
    <InstructionGroup instruction={instruction}>
        {roots.filter((root) => targetMatchesRoot(instruction.target, root)).map((root) => {
            const neckX = (root.cervicalAnchors.left.x + root.cervicalAnchors.right.x) / 2;
            const controlX = (neckX + root.apexAnchor.x) / 2;
            return (
                <path
                    d={`M${neckX},2 Q${controlX},${root.apexAnchor.y * 0.5} ${root.apexAnchor.x},${root.apexAnchor.y - 3}`}
                    fill="none"
                    key={root.outlineRef}
                    stroke={instruction.presentation.stroke}
                    strokeDasharray={instruction.presentation.strokeDasharray}
                    strokeLinecap="round"
                    strokeWidth={instruction.presentation.strokeWidth}
                />
            );
        })}
    </InstructionGroup>
);

const ImplantFixtureInstruction = ({ instruction }) => (
    <InstructionGroup instruction={instruction}>
        <path d="M19,3 L31,3 L32.5,34 L25,44 L17.5,34 Z" fill={instruction.presentation.fill} fillOpacity={instruction.presentation.fillOpacity} stroke={instruction.presentation.stroke} strokeDasharray={instruction.presentation.strokeDasharray} strokeLinejoin="round" strokeWidth={instruction.presentation.strokeWidth} />
        {[10, 15, 20, 25, 30, 35].map((y) => (
            <path d={`M18.5,${y} L31.5,${y}`} fill="none" key={y} stroke={instruction.presentation.stroke} strokeWidth="1.15" />
        ))}
    </InstructionGroup>
);

const RootInstruction = ({ instruction, roots }) => {
    if (instruction.effect === 'endodontic-therapy') {
        return <EndodonticRootInstruction instruction={instruction} roots={roots} />;
    }
    if (instruction.effect === 'implant-fixture') {
        return <ImplantFixtureInstruction instruction={instruction} />;
    }
    if (instruction.effect === 'pain-marker') {
        const root = roots.find((candidate) => targetMatchesRoot(instruction.target, candidate)) ?? roots[0];
        return (
            <InstructionGroup instruction={instruction}>
                <circle cx={root.apexAnchor.x} cy={root.apexAnchor.y - 3} fill={instruction.presentation.fill} r="3.5" stroke={instruction.presentation.stroke} strokeWidth={instruction.presentation.strokeWidth} />
            </InstructionGroup>
        );
    }
    return null;
};

const ROOT_LAYER_ROLES = [
    VISUAL_LAYER_ROLES.FINDINGS,
    VISUAL_LAYER_ROLES.EXISTING_COMPLETED_WORK,
    VISUAL_LAYER_ROLES.PLANNED_ACTIVE_WORK,
];

export const RootVisualLayers = memo(function RootVisualLayers({ roots, toothVisual }) {
    return ROOT_LAYER_ROLES.map((layerRole) => {
        const instructions = getLayerInstructions(toothVisual, layerRole);
        if (instructions.length === 0) return null;
        return (
            <g
                data-layer-index={getLayerIndex(layerRole)}
                data-layer-role={layerRole}
                key={layerRole}
            >
                {instructions.map((instruction) => (
                    <RootInstruction
                        instruction={instruction}
                        key={instruction.instructionId}
                        roots={roots}
                    />
                ))}
            </g>
        );
    });
});
