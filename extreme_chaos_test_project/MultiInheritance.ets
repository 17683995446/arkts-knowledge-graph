/**
 * 多重继承/接口实现测试
 */

interface InterfaceA {
    methodA(): void;
}

interface InterfaceB {
    methodB(): string;
}

interface InterfaceC {
    propC: number;
}

interface InterfaceD extends InterfaceA, InterfaceB {
    methodD(): boolean;
}

export class MultiImplClass implements InterfaceA, InterfaceB, InterfaceC, InterfaceD {
    propC: number = 42;
    
    methodA(): void {
        console.log('methodA');
    }
    
    methodB(): string {
        return 'methodB';
    }
    
    methodD(): boolean {
        return true;
    }
}

export abstract class AbstractBase {
    abstract abstractMethod(): void;
    
    concreteMethod() {
        return 'concrete';
    }
}

export class ConcreteImpl extends AbstractBase {
    abstractMethod(): void {
        console.log('implemented');
    }
}
