/**
 * 调用链文件 8
 */

import { ChainClass9 } from './CallChain9';

export class ChainClass8 {
    methodA() {
        const next = new ChainClass9();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain8 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain8 C';
    }
}
