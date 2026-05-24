/**
 * 调用链文件 3
 */

import { ChainClass4 } from './CallChain4';

export class ChainClass3 {
    methodA() {
        const next = new ChainClass4();
        return next.methodB();
    }
    
    methodB() {
        return 'Chain3 B';
    }
    
    methodC() {
        this.methodA();
        this.methodB();
        return 'Chain3 C';
    }
}
