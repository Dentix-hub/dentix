export default function ApprovedArtworkCrop({ artwork, crop, label, testId, className = '', children }) {
    const [x, y, width, height] = crop;

    return (
        <div
            className={`relative mx-auto h-full w-full overflow-hidden bg-white ${className}`}
            role="img"
            aria-label={label}
            data-testid={testId}
            data-source-crop={`${x},${y},${width},${height}`}
            data-artwork-src={artwork.src}
        >
            <svg
                className="h-full w-full"
                viewBox={`0 0 ${width} ${height}`}
                preserveAspectRatio="xMidYMid meet"
                aria-hidden="true"
                focusable="false"
            >
                <image
                    href={artwork.src}
                    x={-x}
                    y={-y}
                    width={artwork.width}
                    height={artwork.height}
                />
            </svg>
            {children && <div className="absolute inset-0">{children}</div>}
        </div>
    );
}
