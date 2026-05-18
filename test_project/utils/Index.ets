/**
 * 工具索引文件
 */

export * from './HttpUtil'

// 更多工具函数
export class MathUtil {
    static clamp(value: number, min: number, max: number): number {
        return Math.max(min, Math.min(max, value))
    }

    static lerp(start: number, end: number, t: number): number {
        return start + (end - start) * t
    }

    static randomInt(min: number, max: number): number {
        return Math.floor(Math.random() * (max - min + 1)) + min
    }

    static round(value: number, decimals: number = 0): number {
        const factor = Math.pow(10, decimals)
        return Math.round(value * factor) / factor
    }

    static isEven(n: number): boolean {
        return n % 2 === 0
    }

    static isOdd(n: number): boolean {
        return n % 2 !== 0
    }

    static gcd(a: number, b: number): number {
        return b === 0 ? a : MathUtil.gcd(b, a % b)
    }

    static lcm(a: number, b: number): number {
        return Math.abs(a * b) / MathUtil.gcd(a, b)
    }
}

export class ColorUtil {
    static hexToRgb(hex: string): { r: number; g: number; b: number } | null {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null
    }

    static rgbToHex(r: number, g: number, b: number): string {
        return '#' + [r, g, b].map(x => {
            const hex = x.toString(16)
            return hex.length === 1 ? '0' + hex : hex
        }).join('')
    }

    static lighten(hex: string, percent: number): string {
        const rgb = ColorUtil.hexToRgb(hex)
        if (!rgb) return hex
        const amount = Math.round(2.55 * percent)
        return ColorUtil.rgbToHex(
            Math.min(255, rgb.r + amount),
            Math.min(255, rgb.g + amount),
            Math.min(255, rgb.b + amount)
        )
    }

    static darken(hex: string, percent: number): string {
        const rgb = ColorUtil.hexToRgb(hex)
        if (!rgb) return hex
        const amount = Math.round(2.55 * percent)
        return ColorUtil.rgbToHex(
            Math.max(0, rgb.r - amount),
            Math.max(0, rgb.g - amount),
            Math.max(0, rgb.b - amount)
        )
    }
}

export class UrlUtil {
    static parseQuery(url: string): Record<string, string> {
        const query: Record<string, string> = {}
        const queryString = url.split('?')[1]
        if (!queryString) return query

        queryString.split('&').forEach(pair => {
            const [key, value] = pair.split('=')
            if (key) {
                query[decodeURIComponent(key)] = value ? decodeURIComponent(value) : ''
            }
        })

        return query
    }

    static buildQuery(params: Record<string, string | number | boolean>): string {
        return Object.entries(params)
            .filter(([_, v]) => v !== undefined && v !== null)
            .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
            .join('&')
    }

    static joinPath(...parts: string[]): string {
        return parts
            .map((part, i) => {
                if (i === 0) return part.replace(/\/+$/, '')
                if (i === parts.length - 1) return part.replace(/^\/+/, '')
                return part.replace(/^\/+|\/+$/g, '')
            })
            .join('/')
    }
}
