/**
 * 继承层次结构 - 中间层 3
 */

import { BaseClass2 } from './Inheritance2';

export abstract class BaseClass3 extends BaseClass2 {
    intermediateMethod(): void {
        console.log('intermediate method 3');
    }
}
