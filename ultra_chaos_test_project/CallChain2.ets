/**
 * 调用链文件 2
 */

import { ChainClass3 } from './CallChain3';

export class ChainClass2 {
    methodA() {
        const next = new ChainClass3();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain2 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain2 C';
    }
}
