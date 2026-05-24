/**
 * 命名空间测试文件
 */

namespace Namespace8 {
    export const VERSION = '1.0.0';
    
    export class InternalClass {
        name: string;
        
        constructor(name: string) {
            this.name = name;
        }
        
        greet(): string {
            return `Hello, ${this.name}`;
        }
    }
    
    export function helper(): void {
        console.log('helper function');
    }
    
    export namespace Inner {
        export const INNER_CONST = 42;
    }
}

export class UsingNamespace8 {
    useHelper(): void {
        Namespace8.helper();
        const cls = new Namespace8.InternalClass('test');
        cls.greet();
    }
}
